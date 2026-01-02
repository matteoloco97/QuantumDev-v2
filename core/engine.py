import os
import sys
import datetime
import re
import requests
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict
from dotenv import load_dotenv

# Patch percorsi per importare i moduli locali
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from vector_memory import VectorMemory
from tools import AVAILABLE_TOOLS

load_dotenv()

# --- CONFIGURAZIONE ---
LLM_API_URL = "http://localhost:5000/v1/chat/completions"
MODEL_NAME = "DeepSeek-R1-Distill-Qwen-32B-abliterated-Q6_K.gguf"

app = FastAPI(title="Quantum AI API", version="3.6 (Strict Memory)")

# Inizializzazione Memoria
try:
    memory = VectorMemory()
except Exception as e:
    print(f"⚠️ Errore critico inizializzazione Memoria: {e}")
    memory = None

# --- MODELLI DATI ---
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    response: str
    tool_used: Optional[str] = None
    context_used: str

# --- PROMPT SYSTEM (FIX ALLUCINAZIONI) ---
def get_system_prompt():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""
Sei Quantum, un'Intelligenza Strategica Personale.
DATA CORRENTE: {now}

=== PROTOCOLLO MEMORIA (RIGIDO) ===
1. Hai accesso a un blocco <CONTESTO_STORICO> che contiene i ricordi reali.
2. Se l'utente chiede informazioni su SE STESSO, i suoi PROGETTI o le sue PREFERENZE:
   - DEVI basarti ESCLUSIVAMENTE su quanto scritto nel <CONTESTO_STORICO>.
   - Se l'informazione non è presente nel contesto, DEVI RISPONDERE: "Non ho dati in memoria su questo."
   - È ASSOLUTAMENTE VIETATO INVENTARE preferenze, abitudini o dati dell'utente.

=== PROTOCOLLO STRUMENTI ===
1. Se l'utente chiede dati FATTUALI GENERALI (es. "Prezzo Bitcoin", "Meteo", "News"), e non li sai:
   - USA IL TOOL: [TOOL: web_search, query: "..."]

=== STILE RISPOSTA ===
- Sii diretto, tecnico e analitico.
- Niente convenevoli inutili.
- Se il ragionamento è incerto, dichiaralo.
"""

def clean_think_tags(text):
    """Rimuove i tag di ragionamento interno del modello"""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def extract_tool_command(text):
    """Cerca comandi tool nella risposta dell'LLM"""
    pattern = r'\[TOOL:\s*(\w+),\s*query:\s*"([^"]+)"\]'
    match = re.search(pattern, text)
    if match:
        return match.group(1), match.group(2)
    return None, None

async def call_llm(messages, temp=0.3):
    """Chiamata API al server LLM locale"""
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temp, # Abbassato a 0.3 per ridurre allucinazioni
        "max_tokens": 1500
    }
    try:
        response = requests.post(LLM_API_URL, json=payload, timeout=120)
        response.raise_for_status() # Solleva errore se status != 200
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        print(f"❌ ERRORE CHIAMATA LLM: {e}")
        return "Errore critico di connessione al Cervello (LLM)."
    except Exception as e:
        print(f"❌ ERRORE GENERICO LLM: {e}")
        return "Errore nell'elaborazione della risposta."

@app.post("/chat/god-mode", response_model=ChatResponse)
async def god_mode_chat(request: ChatRequest):
    user_input = request.message
    
    # 1. Recupero Intelligente Memoria
    mem_context = "Memoria offline o vuota."
    if memory:
        # La soglia è gestita dentro vector_memory.py ora
        mem_context = memory.search(user_input)
    
    # 2. Costruzione Messaggio
    system_prompt = get_system_prompt()
    full_user_msg = f"<CONTESTO_STORICO>\n{mem_context}\n</CONTESTO_STORICO>\n\nUTENTE:\n{user_input}"
    
    messages = [{"role": "system", "content": system_prompt}]
    if request.history:
        messages.extend(request.history[-4:]) # Mantiene un po' di short-term memory
    messages.append({"role": "user", "content": full_user_msg})

    print(f"⚡ Elaborazione LLM (Input: {user_input[:30]}...)")
    raw_response = await call_llm(messages)
    
    # 3. Tool Logic
    tool_name, tool_query = extract_tool_command(raw_response)
    tool_used = None
    final_response = raw_response

    if tool_name == "web_search":
        print(f"⚙️ Tool Trigger: {tool_query}")
        tool_used = "web_search"
        
        # Verifica se il tool esiste davvero
        if tool_name in AVAILABLE_TOOLS:
            try:
                tool_result = AVAILABLE_TOOLS[tool_name](tool_query)
            except Exception as e:
                tool_result = f"Errore nell'esecuzione del tool: {e}"
            
            # Inietta il risultato e chiedi nuova risposta
            messages.append({"role": "assistant", "content": raw_response})
            messages.append({"role": "system", "content": f"RISULTATI TOOL:\n{tool_result}\n\nUsa questi dati per rispondere all'utente."})
            final_response = await call_llm(messages)
        else:
            final_response += "\n[ERRORE SISTEMA: Tool richiesto non disponibile]"

    clean_response = clean_think_tags(final_response)
    
    # 4. Salvataggio Selettivo
    # Il filtro "anti-spam" è gestito dentro memory.save()
    if memory:
        memory.save(user_input, clean_response)
    
    return {
        "response": clean_response,
        "tool_used": tool_used,
        "context_used": mem_context[:100] + "..." # Log parziale per debug
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
