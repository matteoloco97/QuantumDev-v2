import sys
import os
import datetime
import re
import requests
import asyncio

# --- CONFIGURAZIONE ---
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from vector_memory import VectorMemory
from tools import AVAILABLE_TOOLS

LLM_API_URL = "http://localhost:5000/v1/chat/completions"
MODEL_NAME = "DeepSeek-R1-Distill-Qwen-32B-abliterated-Q6_K.gguf"

# Inizializza memoria o fallback
try:
    memory = VectorMemory()
except:
    class DummyMemory:
        def search(self, q): return "Nessun dato."
        def save(self, u, a): pass
    memory = DummyMemory()

def get_system_prompt():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""
Sei Quantum, un'Assistente AI esperto.
OGGI È: {now}

TUE REGOLE SUPREME:
1. NON INVENTARE. Se non sai un dato aggiornato (prezzi, news, meteo), DEVI usare il tool.
2. NON dialogare con te stesso. Rispondi solo all'ultima domanda dell'utente.
3. Se usi un tool, scrivi ESATTAMENTE e SOLO il comando, nient'altro.

SINTASSI TOOL:
[TOOL: web_search, query: "tua ricerca qui"]
"""

def extract_tool_command(text):
    # Cerca il comando tool ignorando il pensiero <think>...</think>
    pattern = r'\[TOOL:\s*(\w+),\s*query:\s*"([^"]+)"\]'
    match = re.search(pattern, text)
    if match:
        return match.group(1), match.group(2)
    return None, None

def clean_think_tags(text):
    """Rimuove i pensieri dell'AI per mostrare solo la risposta pulita"""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

async def chat_with_llm(messages):
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.3,  # Molto basso per evitare che "sogni"
        "max_tokens": 1000
    }
    try:
        response = requests.post(LLM_API_URL, json=payload, timeout=120)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return f"ERRORE API: {response.status_code}"
    except Exception as e:
        return f"ERRORE CONNESSIONE: {e}"

async def main():
    print(f"\n🚀 Quantum v2.3 (Clean & Focus) - {datetime.datetime.now()}")
    
    # Storico della conversazione corrente (non persistente tra riavvii, quello lo fa Chroma)
    chat_history = [] 

    while True:
        try:
            user_input = input("\nTu: ")
            if user_input.lower() in ["exit", "quit"]: break

            # 1. Recupera Memoria
            mem_context = memory.search(user_input)
            
            # 2. Costruisci il messaggio
            # Mettiamo il contesto NEL MESSAGGIO UTENTE, non come storico, per evitare confusione
            full_user_msg = f"""
<CONTESTO_MEMORIA>
{mem_context}
</CONTESTO_MEMORIA>

DOMANDA UTENTE:
{user_input}
"""
            # Prepariamo la lista messaggi pulita per ogni turno
            current_msgs = [
                {"role": "system", "content": get_system_prompt()},
            ]
            # Aggiungiamo storico recente (max 2 turni) per mantenere il filo
            current_msgs.extend(chat_history[-4:]) 
            current_msgs.append({"role": "user", "content": full_user_msg})

            print("Quantum sta pensando...", end="\r")
            
            # --- PRIMO PASSAGGIO (Decisione) ---
            raw_response = await chat_with_llm(current_msgs)
            
            # Controlliamo se vuole usare un tool
            tool_name, tool_query = extract_tool_command(raw_response)

            final_answer = raw_response

            if tool_name == "web_search":
                print(f"\n⚙️  CERCO SU BRAVE: '{tool_query}'")
                tool_output = AVAILABLE_TOOLS["web_search"](tool_query)
                print(f"✅ TROVATO. Elaborazione...")

                # --- SECONDO PASSAGGIO (Elaborazione Dati) ---
                # Aggiungiamo i risultati alla conversazione
                current_msgs.append({"role": "assistant", "content": raw_response})
                current_msgs.append({"role": "system", "content": f"RISULTATI DAL WEB:\n{tool_output}\n\nOra rispondi alla domanda dell'utente usando questi dati."})
                
                final_answer = await chat_with_llm(current_msgs)

            # Pulizia e Stampa
            clean_answer = clean_think_tags(final_answer)
            print(f"\nQuantum: {clean_answer}")

            # Salviamo nello storico breve e nella memoria a lungo termine
            chat_history.append({"role": "user", "content": user_input})
            chat_history.append({"role": "assistant", "content": final_answer})
            memory.save(user_input, clean_answer)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nErrore Critico: {e}")

if __name__ == "__main__":
    asyncio.run(main())
