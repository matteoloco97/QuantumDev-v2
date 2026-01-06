import os
import sys
import re
import requests
import uvicorn
import asyncio
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from dotenv import load_dotenv

# Setup percorsi
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from vector_memory import VectorMemory
from tools import AVAILABLE_TOOLS

load_dotenv()

# --- CONFIGURAZIONE ---
LLM_API_URL = "http://localhost:5000/v1/chat/completions"
MODEL_NAME = "DeepSeek-R1-Distill-Qwen-32B-abliterated-Q6_K.gguf"

app = FastAPI(title="Quantum AI API", version="9.4 (Dual Core)")

try:
    memory = VectorMemory()
except:
    memory = None
    print("⚠️ Memoria Vettoriale non disponibile.")

# DTO: Aggiunto campo 'mode'
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []
    mode: str = "general"  # Opzioni: "general" | "factory"

class ChatResponse(BaseModel):
    response: str
    tool_used: Optional[str] = None
    context_used: str

def clean_think_tags(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def extract_tool_command(text):
    match = re.search(r'\[TOOL:\s*(\w+),\s*query:\s*"([^"]+)"\]', text, re.DOTALL)
    return (match.group(1), match.group(2)) if match else (None, None)

async def analyze_and_save_memory(user_input: str, ai_response: str):
    """Salva solo se siamo in modalità General."""
    if not memory: return
    try:
        if len(user_input) < 10 or "ci sei" in user_input.lower(): return 
        
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": f"Estrai SOLO preferenze utente o vincoli tecnici. No riassunti. Input: {user_input}"}],
            "temperature": 0.1, "max_tokens": 150
        }
        resp = requests.post(LLM_API_URL, json=payload, timeout=20)
        content = clean_think_tags(resp.json()['choices'][0]['message']['content'])
        if len(content) > 5 and "SKIP" not in content:
            memory.save(user_input, content)
            print(f"💾 [MEMORIA] Salvato: {content[:40]}...")
    except: pass

async def call_llm(messages, temperature=0.3):
    payload = {
        "model": MODEL_NAME, "messages": messages,
        "temperature": temperature, "max_tokens": 8000
    }
    try:
        response = requests.post(LLM_API_URL, json=payload, timeout=300)
        return response.json()['choices'][0]['message']['content']
    except Exception as e: return f"Errore LLM: {e}"

@app.post("/chat/god-mode", response_model=ChatResponse)
async def god_mode_chat(request: ChatRequest, background_tasks: BackgroundTasks):
    user_input = request.message
    mode = request.mode
    
    # --- DUAL CORE LOGIC ---
    
    if mode == "factory":
        # MODALITÀ FACTORY: Isolamento Totale
        # 1. Niente memoria storica (evita inquinamento)
        mem_context = "NESSUNA MEMORIA STORICA DISPONIBILE. BASATI SOLO SUL CONTESTO ATTUALE."
        
        # 2. Prompt da Esecutore Tecnico
        system_prompt = f"""
        SEI 'QUANTUM BUILDER'. Un motore di esecuzione software automatizzato.
        
        IL TUO UNICO OBIETTIVO:
        Ricevere un task -> Scrivere il codice -> Eseguire il codice.
        
        REGOLE FERREE:
        1. NON usare la memoria a lungo termine. Usa solo i file che vedi ora.
        2. NON fare conversazione. Non dire "Ecco il codice". 
        3. Se ti viene chiesto di scrivere un file, usa [TOOL: write_file].
        4. Se ti viene chiesto di eseguire, usa [TOOL: terminal_run].
        5. RAGIONA sui problemi tecnici (dentro i tag <think>), ma l'output finale deve essere l'azione.
        
        TOOLS DISPONIBILI:
        {list(AVAILABLE_TOOLS.keys())}
        """
        temp = 0.1 # Temperatura bassissima per precisione chirurgica

    else:
        # MODALITÀ GENERAL: Intelligenza Completa
        mem_context = memory.search(user_input) if memory else ""
        system_prompt = f"""
        SEI 'QUANTUM OS'. L'Intelligenza Centrale.
        Sei un consulente esperto, diretto e razionale.
        Usa la memoria storica per personalizzare le risposte.
        
        CONTESTO MEMORIA:
        {mem_context}
        """
        temp = 0.4 # Più creativo

    # Costruzione messaggi
    messages = [{"role": "system", "content": system_prompt}]
    if request.history: messages.extend(request.history[-6:])
    messages.append({"role": "user", "content": user_input})

    print(f"🧠 [{mode.upper()}] INPUT: {user_input[:50]}...")
    
    # Esecuzione
    raw_response = await call_llm(messages, temperature=temp)
    
    # Gestione Tool
    tool_name, tool_query = extract_tool_command(raw_response)
    tool_used = None
    final_response = raw_response

    if tool_name and tool_name in AVAILABLE_TOOLS:
        print(f"⚙ EXEC TOOL: {tool_name} -> {tool_query[:30]}...")
        if tool_name == "write_file" and "|" in tool_query:
            try:
                fname, fcontent = tool_query.split("|", 1)
                tool_result = AVAILABLE_TOOLS[tool_name](fname.strip(), fcontent.strip())
            except: tool_result = "Errore sintassi."
        else:
            tool_result = AVAILABLE_TOOLS[tool_name](tool_query)
            
        tool_used = tool_name
        messages.append({"role": "assistant", "content": raw_response})
        messages.append({"role": "system", "content": f"TOOL OUTPUT: {tool_result}. Ora concludi."})
        final_response = await call_llm(messages, temperature=temp)
    
    clean_response = clean_think_tags(final_response)
    
    # Salva memoria SOLO se in modalità General
    if mode == "general" and memory:
        background_tasks.add_task(analyze_and_save_memory, user_input, clean_response)
    
    return {
        "response": clean_response,
        "tool_used": tool_used,
        "context_used": mem_context[:30] + "..."
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
