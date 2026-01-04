import os
import sys
import datetime
import re
import requests
import uvicorn
import asyncio
import numpy as np
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from vector_memory import VectorMemory
from tools import AVAILABLE_TOOLS

load_dotenv()

# CONFIGURAZIONE
LLM_API_URL = "http://localhost:5000/v1/chat/completions"
MODEL_NAME = "DeepSeek-R1-Distill-Qwen-32B-abliterated-Q6_K.gguf"

print("🧠 Caricamento Semantic Router (MiniLM)...")
try:
    router_model = SentenceTransformer('all-MiniLM-L6-v2')
    # CONCETTI PESANTI (Il DNA dell'Analista)
    DEEP_CONCEPTS = [
        "analizza la situazione", "crea una strategia", "calcola le probabilità",
        "scrivi codice python", "spiegami il motivo", "fai una previsione",
        "studia il file", "report dettagliato", "confronta i dati", 
        "pianificazione finanziaria", "esamina le quote", "cerca valore", 
        "risk management", "studio approfondito", "betting exchange", "scommesse"
    ]
    deep_vectors = router_model.encode(DEEP_CONCEPTS)
    print("✅ Semantic Router Attivo.")
except Exception as e:
    print(f"⚠️ Errore caricamento Router: {e}. Si userà fallback.")
    router_model = None

app = FastAPI(title="Quantum AI API", version="7.1 (Tuned Router)")

try:
    memory = VectorMemory()
except:
    memory = None

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    response: str
    tool_used: Optional[str] = None
    context_used: str

def detect_intent_semantic(user_input):
    clean_input = user_input.lower().strip()
    
    # 1. FILTRO MANUALE ESTESO (Speed Assoluta)
    # Se contiene parole di saluto, forza SPEED ignorando la semantica
    speed_triggers = ["ciao", "hola", "test", "chi sei", "come va", "buongiorno", "ehi", "ci sei", "tutto bene"]
    if any(trigger in clean_input for trigger in speed_triggers) and len(clean_input.split()) < 5:
        return {"mode": "⚡ SPEED (Manual)", "score": 0.0}

    # 2. Se il router non va, fallback su lunghezza
    if router_model is None:
        return {"mode": "🧠 DEEP (Fallback)", "score": 1.0} if len(clean_input.split()) > 6 else {"mode": "⚡ SPEED (Fallback)", "score": 0.0}

    # 3. Analisi Semantica
    try:
        input_vector = router_model.encode([user_input])
        similarities = cosine_similarity(input_vector, deep_vectors)
        max_similarity = float(np.max(similarities))
        
        # NUOVA SOGLIA: 0.60 (Più severa)
        if max_similarity > 0.60:
            return {
                "mode": "🧠 DEEP THINK (Semantic)",
                "temperature": 0.6,
                "max_tokens": 8000,
                "system_instruction": "Usa il ragionamento profondo (<think>). Analizza il problema passo dopo passo. Sii dettagliato.",
                "score": max_similarity
            }
        else:
            return {
                "mode": "⚡ SPEED (Semantic)",
                "temperature": 0.1,
                "max_tokens": 200, # Strozzatura massima
                "system_instruction": "RISPONDI SUBITO IN ITALIANO. Sii breve, colloquiale e diretto. NON avviare ragionamenti complessi.",
                "score": max_similarity
            }
    except:
        return {"mode": "⚡ SPEED (Error)", "score": 0.0}

def clean_think_tags(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

async def analyze_and_save_memory(user_input: str, ai_response: str):
    if not memory: return
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": f"Estrai FATTO o 'SKIP'. In: {user_input} | Out: {ai_response}"}],
            "temperature": 0.1, "max_tokens": 150
        }
        resp = requests.post(LLM_API_URL, json=payload, timeout=30)
        content = clean_think_tags(resp.json()['choices'][0]['message']['content'])
        if "SKIP" not in content and len(content) > 5:
            memory.save(user_input, content)
    except: pass

def extract_tool_command(text):
    match = re.search(r'\[TOOL:\s*(\w+),\s*query:\s*"([^"]+)"\]', text)
    return (match.group(1), match.group(2)) if match else (None, None)

async def call_llm(messages, config):
    payload = {
        "model": MODEL_NAME, "messages": messages,
        "temperature": config.get("temperature", 0.3), "max_tokens": config.get("max_tokens", 2000)
    }
    try:
        response = requests.post(LLM_API_URL, json=payload, timeout=120)
        return response.json()['choices'][0]['message']['content']
    except: return "Errore LLM."

@app.post("/chat/god-mode", response_model=ChatResponse)
async def god_mode_chat(request: ChatRequest, background_tasks: BackgroundTasks):
    user_input = request.message
    
    # 1. Router Decision
    config = detect_intent_semantic(user_input)
    print(f"🚦 ROUTER: {config['mode']} (Score: {config.get('score', 0):.2f})")

    mem_context = memory.search(user_input) if memory else "Nessuna."
    
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    system_prompt = f"""
    Sei Quantum. DATA: {now}
    MODE: {config['mode']}
    ISTRUZIONI: {config.get('system_instruction', '')}
    
    MEMORY:
    {mem_context}
    
    Se mancano dati live, usa [TOOL: web_search]
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    if request.history: messages.extend(request.history[-4:])
    messages.append({"role": "user", "content": user_input})

    # 2. Esecuzione
    raw_response = await call_llm(messages, config)
    
    # 3. Tool Logic
    tool_name, tool_query = extract_tool_command(raw_response)
    tool_used = None
    final_response = raw_response

    if tool_name == "web_search" and tool_name in AVAILABLE_TOOLS:
        print(f"⚙️ Tool: {tool_query}")
        tool_used = "web_search"
        tool_result = AVAILABLE_TOOLS[tool_name](tool_query)
        messages.append({"role": "assistant", "content": raw_response})
        messages.append({"role": "system", "content": f"DATI TOOL: {tool_result}"})
        
        final_response = await call_llm(messages, {"temperature": 0.5, "max_tokens": 5000})
    
    clean_response = clean_think_tags(final_response)
    
    if memory:
        background_tasks.add_task(analyze_and_save_memory, user_input, clean_response)
    
    return {
        "response": clean_response,
        "tool_used": tool_used,
        "context_used": mem_context[:100] + "..."
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
