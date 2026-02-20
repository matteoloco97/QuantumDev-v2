import os
import sys
import re
import json
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

# --- GENERAL INTELLIGENCE TOOL CONFIG ---
GENERAL_TOOLS_ENABLED = int(os.getenv("GENERAL_TOOLS_ENABLED", "1"))
GENERAL_MAX_TOOL_CALLS = int(os.getenv("GENERAL_MAX_TOOL_CALLS", "3"))
GENERAL_ALLOW_TERMINAL_RUN = int(os.getenv("GENERAL_ALLOW_TERMINAL_RUN", "0"))
GENERAL_ALLOW_WRITE_PROJECTS = int(os.getenv("GENERAL_ALLOW_WRITE_PROJECTS", "0"))

app = FastAPI(title="Quantum AI API", version="9.6 (Tool Execution Fixed)")

try:
    memory = VectorMemory()
except:
    memory = None
    print("⚠️ Memoria Vettoriale non disponibile.")

# DTO
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []
    mode: str = "general"

class ChatResponse(BaseModel):
    response: str
    tool_used: Optional[str] = None
    context_used: str

def clean_think_tags(text):
    """Rimuove <think> tags di DeepSeek-R1"""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def extract_tool_command(text):
    """
    🔧 FIXED: Gestisce formati multipli (DeepSeek-R1 compatible)
    """
    # Formato 1: [TOOL: nome, query: "..."]
    match = re.search(r'\[TOOL:\s*(\w+),\s*query:\s*"([^"]+)"\]', text, re.DOTALL)
    if match:
        return (match.group(1), match.group(2))
    
    # Formato 2: [TOOL: nome]\n{"command": "..."} (DeepSeek-R1 style)
    match = re.search(r'\[TOOL:\s*(\w+)\]\s*\n?\s*\{[^}]*"command":\s*"([^"]+)"', text, re.DOTALL)
    if match:
        return (match.group(1), match.group(2))
    
    # Formato 3: [TOOL: nome]\n{"query": "..."}
    match = re.search(r'\[TOOL:\s*(\w+)\]\s*\n?\s*\{[^}]*"query":\s*"([^"]+)"', text, re.DOTALL)
    if match:
        return (match.group(1), match.group(2))
    
    return (None, None)

async def analyze_and_save_memory(user_input: str, ai_response: str):
    """Pulisce <think> tags PRIMA di salvare in memoria"""
    if not memory: 
        return
    
    try:
        clean_input = clean_think_tags(user_input)
        clean_response = clean_think_tags(ai_response)
        
        if len(clean_input) < 10 or "ci sei" in clean_input.lower(): 
            return 
        
        payload = {
            "model": MODEL_NAME,
            "messages": [{
                "role": "user", 
                "content": f"Estrai SOLO preferenze utente o vincoli tecnici rilevanti. No reasoning. No think tags. SOLO fatti concreti. Input: {clean_input}"
            }],
            "temperature": 0.05,
            "max_tokens": 150
        }
        
        resp = requests.post(LLM_API_URL, json=payload, timeout=20)
        content = resp.json()['choices'][0]['message']['content']
        content = clean_think_tags(content)
        
        if len(content) > 5 and "SKIP" not in content.upper() and "<think>" not in content.lower():
            memory.save(clean_input, content)
            print(f"💾 [MEMORIA] Salvato: {content[:40]}...")
        else:
            print(f"⏭️  [MEMORIA] Skipped (non rilevante o contiene think tags)")
            
    except Exception as e:
        print(f"⚠️ Errore memoria: {e}")

async def call_llm(messages, temperature=0.3):
    """Temperature calibrate per DeepSeek-R1"""
    payload = {
        "model": MODEL_NAME, 
        "messages": messages,
        "temperature": temperature, 
        "max_tokens": 8000
    }
    try:
        response = requests.post(LLM_API_URL, json=payload, timeout=300)
        return response.json()['choices'][0]['message']['content']
    except Exception as e: 
        return f"Errore LLM: {e}"

@app.post("/chat/god-mode", response_model=ChatResponse)
async def god_mode_chat(request: ChatRequest, background_tasks: BackgroundTasks):
    user_input = request.message
    mode = request.mode
    
    if mode == "factory":
        mem_context = "NESSUNA MEMORIA STORICA DISPONIBILE. BASATI SOLO SUL CONTESTO ATTUALE."
        
        system_prompt = f"""
        SEI 'QUANTUM BUILDER'. Un motore di esecuzione software automatizzato.
        
        IL TUO UNICO OBIETTIVO:
        Ricevere un task -> Analizzare (dentro <think>) -> Eseguire il codice/comando.
        
        REGOLE FERREE:
        1. NON usare la memoria a lungo termine. Usa solo i file che vedi ora.
        2. NON fare conversazione. Non dire "Ecco il codice". 
        3. Ragiona dentro <think>...</think>, poi genera l'output richiesto.
        4. Se ti viene chiesto di scrivere un file, usa [TOOL: write_file, query: "filename|content"].
        5. Se ti viene chiesto di eseguire, usa [TOOL: terminal_run, query: "command"].
        
        TOOLS DISPONIBILI:
        {list(AVAILABLE_TOOLS.keys())}
        """
        temp = 0.05

    else:
        mem_context = memory.search(user_input) if memory else "Nessuna memoria disponibile."

        _tool_list = ["web_search", "read_url", "write_file"]
        if GENERAL_ALLOW_TERMINAL_RUN:
            _tool_list.append("terminal_run")
        _write_dirs = "memories/ e projects/" if GENERAL_ALLOW_WRITE_PROJECTS else "memories/ (solo)"
        _terminal_note = (
            "- terminal_run: esegue comandi di sistema. Usalo solo se esplicitamente richiesto."
            if GENERAL_ALLOW_TERMINAL_RUN else
            "- NON usare terminal_run (disabilitato in questa modalità)."
        )

        system_prompt = f"""
        SEI 'QUANTUM OS'. L'Intelligenza Centrale powered by DeepSeek-R1.
        Sei un consulente esperto, diretto e razionale.

        Usa <think> tags per il tuo reasoning interno, poi rispondi in modo naturale.
        Usa la memoria storica per personalizzare le risposte.

        TOOL DISPONIBILI: {_tool_list}
        - web_search: cerca informazioni aggiornate sul web. Usalo per domande su fatti recenti, notizie, prezzi.
        - read_url: legge il contenuto di un URL. Usalo quando ti viene fornito un link o devi accedere a documentazione online.
        - write_file: salva testo su file in {_write_dirs}. Usalo solo per salvare note/informazioni esplicitamente richieste.
        {_terminal_note}

        FORMATO OBBLIGATORIO PER TOOL CALL (usa ESATTAMENTE questo formato, nessuna variazione):
        [TOOL: nome_tool, query: "parametro"]
        Per write_file: [TOOL: write_file, query: "filename|content"]

        REGOLE:
        1. Usa un tool SOLO se strettamente necessario per rispondere.
        2. NON usare tool non presenti nell'elenco sopra.
        3. Un solo tool per risposta; attendi il risultato prima di procedere.

        CONTESTO MEMORIA:
        {mem_context}
        """
        temp = 0.4

    messages = [{"role": "system", "content": system_prompt}]
    if request.history: 
        messages.extend(request.history[-6:])
    messages.append({"role": "user", "content": user_input})

    print(f"🧠 [{mode.upper()}] INPUT: {user_input[:50]}...")

    raw_response = await call_llm(messages, temperature=temp)
    tool_used = None
    final_response = raw_response

    if mode == "general" and GENERAL_TOOLS_ENABLED:
        # Build allowed tools with guardrails
        allowed_tools = {k: v for k, v in AVAILABLE_TOOLS.items()}
        if not GENERAL_ALLOW_TERMINAL_RUN:
            allowed_tools.pop("terminal_run", None)

        for step in range(GENERAL_MAX_TOOL_CALLS):
            tool_name, tool_query = extract_tool_command(raw_response)
            if not tool_name or tool_name not in allowed_tools:
                break

            # write_file guardrail: general mode restricts to memories/ by default
            if tool_name == "write_file" and not GENERAL_ALLOW_WRITE_PROJECTS:
                fname = tool_query.split("|", 1)[0].strip() if "|" in tool_query else tool_query.strip()
                fname_norm = os.path.normpath(fname)
                if not (fname_norm == "memories" or fname_norm.startswith("memories" + os.sep)):
                    tool_result = (
                        "ERRORE GUARDRAIL: write_file in modalità general è consentito solo in memories/ "
                        "(imposta GENERAL_ALLOW_WRITE_PROJECTS=1 per abilitare projects/)."
                    )
                    print(f"🚫 [GENERAL GUARDRAIL] write_file bloccato: path '{fname[:30]}'")
                    messages.append({"role": "assistant", "content": raw_response})
                    messages.append({"role": "system", "content": f"TOOL OUTPUT: {tool_result}. Informa l'utente e suggerisci di usare memories/."})
                    raw_response = await call_llm(messages, temperature=temp)
                    final_response = raw_response
                    break

            query_preview = tool_query[:50].replace('\n', ' ')
            print(f"⚙️ [GENERAL TOOL {step + 1}/{GENERAL_MAX_TOOL_CALLS}] {tool_name} -> '{query_preview}'")

            if tool_name == "write_file" and "|" in tool_query:
                try:
                    fname, fcontent = tool_query.split("|", 1)
                    tool_result = AVAILABLE_TOOLS[tool_name](fname.strip(), fcontent.strip())
                except Exception:
                    tool_result = "Errore sintassi write_file."
            else:
                tool_result = AVAILABLE_TOOLS[tool_name](tool_query)

            tool_used = tool_name
            messages.append({"role": "assistant", "content": raw_response})
            messages.append({"role": "system", "content": f"TOOL OUTPUT: {tool_result}. Continua la risposta."})
            raw_response = await call_llm(messages, temperature=temp)
            final_response = raw_response

    else:
        # Factory mode (or general with tools disabled): single tool call – unchanged behaviour
        tool_name, tool_query = extract_tool_command(raw_response)
        if tool_name and tool_name in AVAILABLE_TOOLS:
            print(f"⚙️ EXEC TOOL: {tool_name} -> {tool_query[:30]}...")

            if tool_name == "write_file" and "|" in tool_query:
                try:
                    fname, fcontent = tool_query.split("|", 1)
                    tool_result = AVAILABLE_TOOLS[tool_name](fname.strip(), fcontent.strip())
                except Exception:
                    tool_result = "Errore sintassi write_file."
            else:
                tool_result = AVAILABLE_TOOLS[tool_name](tool_query)

            tool_used = tool_name
            messages.append({"role": "assistant", "content": raw_response})
            messages.append({"role": "system", "content": f"TOOL OUTPUT: {tool_result}. Ora concludi."})
            final_response = await call_llm(messages, temperature=temp)
    
    clean_response = clean_think_tags(final_response)
    
    if mode == "general" and memory:
        background_tasks.add_task(analyze_and_save_memory, user_input, clean_response)
    
    return {
        "response": clean_response,
        "tool_used": tool_used,
        "context_used": mem_context[:30] + "..." if mem_context else "N/A"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
