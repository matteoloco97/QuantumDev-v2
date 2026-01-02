import os
import sys
import datetime
import re
import requests
import uvicorn
import asyncio
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from vector_memory import VectorMemory
from tools import AVAILABLE_TOOLS

load_dotenv()

# CONFIGURAZIONE
LLM_API_URL = "http://localhost:5000/v1/chat/completions"
MODEL_NAME = "DeepSeek-R1-Distill-Qwen-32B-abliterated-Q6_K.gguf"

app = FastAPI(title="Quantum AI API", version="4.2 (Speed Optimized)")

try:
    memory = VectorMemory()
except Exception as e:
    print(f"⚠️ Errore Memoria: {e}")
    memory = None

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    response: str
    tool_used: Optional[str] = None
    context_used: str

def get_system_prompt(user_input):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""
Sei Quantum.
DATA: {now}

=== MODALITÀ PENSIERO (CRUCIALE) ===
1. Se l'utente saluta o fa domande semplici -> RISPONDI SUBITO. Non generare pensieri complessi. Sii istantaneo.
2. Se l'utente chiede ANALISI, STRATEGIE o CODICE -> Usa la tua logica profonda (<think>) per ragionare passo dopo passo.

=== DIRETTIVE ===
- MEMORIA: Usa <CONTESTO_STORICO> per i fatti passati.
- TOOL: Usa [TOOL: web_search] solo per dati live mancanti.
- STILE: Diretto, professionale, nessun riassunto inutile.
"""

def clean_think_tags(text):
    """Rimuove i pensieri interni del modello"""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

async def analyze_and_save_memory(user_input: str, ai_response: str):
    if not memory:
        return

    extraction_prompt = f"""
    Estrai SOLO fatti o preferenze a lungo termine da questo scambio.
    UTENTE: {user_input}
    AI: {ai_response}
    Output: "SKIP" se inutile, oppure il fatto in una frase.
    """
    
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": extraction_prompt}],
        "temperature": 0.1,
        "max_tokens": 150
    }
    
    try:
        response = requests.post(LLM_API_URL, json=payload, timeout=60)
        raw = response.json()['choices'][0]['message']['content']
        content = clean_think_tags(raw)
        
        if "SKIP" not in content and len(content) > 5:
            memory.save(user_input, content)
            
    except Exception as e:
        print(f"⚠️ Errore Background: {e}")

def extract_tool_command(text):
    pattern = r'\[TOOL:\s*(\w+),\s*query:\s*"([^"]+)"\]'
    match = re.search(pattern, text)
    if match:
        return match.group(1), match.group(2)
    return None, None

async def call_llm(messages, temp=0.3):
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temp,
        "max_tokens": 1500
    }
    try:
        response = requests.post(LLM_API_URL, json=payload, timeout=120)
        return response.json()['choices'][0]['message']['content']
    except:
        return "Errore connessione LLM."

@app.post("/chat/god-mode", response_model=ChatResponse)
async def god_mode_chat(request: ChatRequest, background_tasks: BackgroundTasks):
    user_input = request.message
    
    mem_context = memory.search(user_input) if memory else "Nessuna."
    
    # Passiamo l'input al prompt generator per decidere la modalità
    system_prompt = get_system_prompt(user_input)
    full_user_msg = f"<CONTESTO_STORICO>\n{mem_context}\n</CONTESTO_STORICO>\n\nUTENTE:\n{user_input}"
    
    messages = [{"role": "system", "content": system_prompt}]
    if request.history:
        messages.extend(request.history[-4:])
    messages.append({"role": "user", "content": full_user_msg})

    print(f"⚡ Elaborazione...")
    raw_response = await call_llm(messages)
    
    tool_name, tool_query = extract_tool_command(raw_response)
    tool_used = None
    final_response = raw_response

    if tool_name == "web_search":
        print(f"⚙️ Tool: {tool_query}")
        tool_used = "web_search"
        if tool_name in AVAILABLE_TOOLS:
            tool_result = AVAILABLE_TOOLS[tool_name](tool_query)
            messages.append({"role": "assistant", "content": raw_response})
            messages.append({"role": "system", "content": f"DATI TOOL:\n{tool_result}"})
            final_response = await call_llm(messages)
    
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
