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

# Setup percorsi
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import moduli interni
from vector_memory import VectorMemory
from tools import AVAILABLE_TOOLS

load_dotenv()

# --- CONFIGURAZIONE ---
LLM_API_URL = "http://localhost:5000/v1/chat/completions"
MODEL_NAME = "DeepSeek-R1-Distill-Qwen-32B-abliterated-Q6_K.gguf"

print("🧠 Caricamento Semantic Router (MiniLM)...")
try:
    router_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # CONCETTI "DEEP" (Analisi + Coding)
    DEEP_CONCEPTS = [
        "analizza la situazione", "crea una strategia", "calcola le probabilità",
        "esamina le quote", "cerca valore", "risk management", "scommesse",
        "scrivi codice", "crea script", "debug", "refactoring", 
        "esegui comando", "terminale", "installare", "pip install", 
        "leggi file", "analizza progetto", "errore python", "fix bug"
    ]
    deep_vectors = router_model.encode(DEEP_CONCEPTS)
    print("✅ Semantic Router Attivo.")
except Exception as e:
    print(f"⚠ Errore Router: {e}. Fallback attivo.")
    router_model = None

app = FastAPI(title="Quantum AI API", version="7.6 (Keyword Override)")

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

# --- NUOVA LOGICA ROUTING CON OVERRIDE ---
def detect_intent_semantic(user_input):
    clean_input = user_input.lower().strip()
    
    # 1. KEYWORD OVERRIDE (Se sento parole tecniche, FORZO la modalità DEEP)
    tech_keywords = ["python", "script", "code", "json", "api", "def ", "import ", "write_file", "terminal_run", "requirements", "crea file"]
    if any(k in clean_input for k in tech_keywords):
        return {
            "mode": "🧠 DEEP THINK (Keyword Override)",
            "temperature": 0.5,
            "max_tokens": 8000,
            "system_instruction": "Sei Quantum Dev. Modalità Engineering. Pensa a fondo. Scrivi codice completo e funzionante.",
            "score": 1.0
        }

    # 2. Filtro Speed (Saluti/Chat rapida)
    speed_triggers = ["ciao", "hola", "test", "chi sei", "come va", "sei vivo"]
    if any(trigger in clean_input for trigger in speed_triggers) and len(clean_input.split()) < 5:
        return {"mode": "⚡ SPEED (Manual)", "score": 0.0}

    # 3. Fallback se router off
    if router_model is None:
        return {"mode": "🧠 DEEP (Fallback)", "score": 1.0}

    # 4. Analisi Semantica (Soglia abbassata a 0.35 per sicurezza)
    try:
        input_vector = router_model.encode([user_input])
        similarities = cosine_similarity(input_vector, deep_vectors)
        max_similarity = float(np.max(similarities))
        
        if max_similarity > 0.35: 
            return {
                "mode": "🧠 DEEP THINK (Semantic)",
                "temperature": 0.5,
                "max_tokens": 8000,
                "system_instruction": "Sei Quantum Dev, un Senior AI Engineer autonomo. Pensa profondamente (<think>) prima di agire.",
                "score": max_similarity
            }
        else:
            return {
                "mode": "⚡ SPEED (Chat)",
                "temperature": 0.1,
                "max_tokens": 500, 
                "system_instruction": "Rispondi in modo diretto.",
                "score": max_similarity
            }
    except:
        return {"mode": "⚡ SPEED (Error)", "score": 0.0}

def clean_think_tags(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def extract_tool_command(text):
    match = re.search(r'\[TOOL:\s*(\w+),\s*query:\s*"([^"]+)"\]', text, re.DOTALL)
    return (match.group(1), match.group(2)) if match else (None, None)

async def analyze_and_save_memory(user_input: str, ai_response: str):
    if not memory: return
    try:
        if "OUTPUT TERMINALE" in ai_response or len(ai_response) < 10: return 
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": f"Estrai un FATTO utile o rispondi 'SKIP'. User: {user_input} | AI: {ai_response}"}],
            "temperature": 0.1, "max_tokens": 150
        }
        resp = requests.post(LLM_API_URL, json=payload, timeout=20)
        content = clean_think_tags(resp.json()['choices'][0]['message']['content'])
        if "SKIP" not in content:
            memory.save(user_input, content)
    except: pass

async def call_llm(messages, config):
    payload = {
        "model": MODEL_NAME, "messages": messages,
        "temperature": config.get("temperature", 0.3), "max_tokens": config.get("max_tokens", 2000)
    }
    try:
        response = requests.post(LLM_API_URL, json=payload, timeout=120)
        return response.json()['choices'][0]['message']['content']
    except Exception as e: return f"Errore LLM: {e}"

@app.post("/chat/god-mode", response_model=ChatResponse)
async def god_mode_chat(request: ChatRequest, background_tasks: BackgroundTasks):
    user_input = request.message
    
    # 1. Routing
    config = detect_intent_semantic(user_input)
    print(f"🚦 ROUTER: {config['mode']} (Score: {config.get('score', 0):.2f})")

    mem_context = memory.search(user_input) if memory else "Nessuna."
    
    # 2. System Prompt V7.6
    system_prompt = f"""
    Sei Quantum Dev (Engine V7.6). MODE: {config['mode']}
    
    TOOLKIT:
    1. [TOOL: list_files, query: "."] -> Vedi file.
    2. [TOOL: read_file, query: "percorso/file.py"] -> Leggi codice.
    3. [TOOL: write_file, query: "nome.py|codice"] -> SCRIVI codice.
    4. [TOOL: terminal_run, query: "comando"] -> ESEGUI comandi (Safety: Richiedi conferma).
    5. [TOOL: web_search, query: "ricerca"] -> Cerca web.

    REGOLE:
    - Scrittura (`write_file`): AUTONOMO.
    - Esecuzione (`terminal_run`): CHIEDI CONFERMA all'utente (Human-in-the-Loop) prima di lanciare.
    
    MEMORIA: {mem_context}
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    if request.history: messages.extend(request.history[-4:])
    messages.append({"role": "user", "content": user_input})

    raw_response = await call_llm(messages, config)
    
    # 3. Tool Logic
    tool_name, tool_query = extract_tool_command(raw_response)
    tool_used = None
    final_response = raw_response

    if tool_name and tool_name in AVAILABLE_TOOLS:
        print(f"⚙ EXEC TOOL: {tool_name}")
        if tool_name == "write_file" and "|" in tool_query:
            try:
                fname, fcontent = tool_query.split("|", 1)
                tool_result = AVAILABLE_TOOLS[tool_name](fname.strip(), fcontent.strip())
            except ValueError:
                tool_result = "Errore formato write_file."
        else:
            tool_result = AVAILABLE_TOOLS[tool_name](tool_query)
            
        tool_used = tool_name
        messages.append({"role": "assistant", "content": raw_response})
        messages.append({"role": "system", "content": f"RISULTATO TOOL: {tool_result}. Procedi."})
        final_response = await call_llm(messages, {"temperature": 0.4, "max_tokens": 4000})
    
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
