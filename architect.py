import requests
import json
import os
import subprocess
import re
import ast

# CONFIGURAZIONE
API_URL = "http://localhost:8001/chat/god-mode"
BASE_DIR = "projects"

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    GREY = '\033[90m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_box(title, content, color=Colors.CYAN):
    print(f"\n{color}┌─ {title} {'─' * (60 - len(title))}┐{Colors.ENDC}")
    lines = content.split('\n')
    for line in lines:
        while len(line) > 60:
            print(f"{color}│ {line[:60]}{Colors.ENDC}")
            line = line[60:]
        print(f"{color}│ {line}{' ' * (60 - len(line))}│{Colors.ENDC}")
    print(f"{color}└{'─' * 63}┘{Colors.ENDC}")

def extract_thought(text):
    think_match = re.search(r'<think>(.*?)</think>', text, re.DOTALL)
    thought = think_match.group(1).strip() if think_match else "Analisi implicita..."
    final_response = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    return thought, final_response

def extract_code_block(text):
    """
    Estrae il codice dai blocchi markdown.
    FIX V13.2: Regex migliorato per accettare qualsiasi tag (text, txt, python) o nessuno.
    """
    # [\w+\-]* -> Accetta parole, trattini o nulla dopo i backtick
    match = re.search(r'```[\w+\-]*\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def extract_json_list(text):
    """Estrae una lista JSON dalla risposta dell'AI."""
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except:
        pass
    return None

def call_ai(message, history=[]):
    payload = {"message": message, "history": history}
    try:
        resp = requests.post(API_URL, json=payload, timeout=300)
        return resp.json().get("response", "")
    except Exception as e:
        return f"ERRORE API: {e}"

def main():
    os.system('clear')
    print(f"{Colors.HEADER}╔══════════════════════════════════════════════════════════╗")
    print(f"║     QUANTUM ARCHITECT V13.2 (Robust & Pragmatic)         ║")
    print(f"╚══════════════════════════════════════════════════════════╝{Colors.ENDC}")
    
    p_name = input(f"{Colors.CYAN}Nome Progetto: {Colors.ENDC}").strip().replace(" ", "_")
    if not p_name: p_name = "project_dynamic"
    
    project_root = os.path.join(BASE_DIR, p_name)
    if not os.path.exists(project_root):
        os.makedirs(project_root)

    user_goal = input(f"{Colors.CYAN}Descrivi il Software: {Colors.ENDC}")

    history = []

    # --- FASE 1: BLUEPRINT (PIANIFICAZIONE STRUTTURA) ---
    print(f"\n{Colors.HEADER}--- FASE 1: ARCHITETTURA E PIANIFICAZIONE ---{Colors.ENDC}")
    
    # FIX V13.2: Prompt "Pragmatico" per evitare over-engineering
    blueprint_prompt = f"""
    SEI UN SOFTWARE ARCHITECT PRAGMATICO.
    OBIETTIVO UTENTE: {user_goal}
    
    TASK:
    Definisci la lista esatta dei file da creare.
    
    REGOLE CRITICHE:
    1. ANALISI RICHIESTA: Se l'utente ha elencato dei file specifici (es. "Voglio main.py, scraper.py"), DEVI RISPETTARE ESATTAMENTE QUELLA LISTA. Non aggiungere cartelle 'src', 'docs' o 'tests' se non richieste.
    2. SOLO SE L'UTENTE È VAGO: Allora e solo allora decidi tu la struttura migliore.
    3. SEMPLICITÀ: Prediligi una struttura piatta (file nella root) per progetti piccoli.
    4. FORMATO: Rispondi ESCLUSIVAMENTE con una lista JSON di stringhe.
    
    ESEMPIO OUTPUT VALIDO:
    ["README.md", "requirements.txt", "database.py", "scraper.py", "main.py"]
    """
    
    print(f"{Colors.BLUE}Generazione Blueprint...{Colors.ENDC}")
    resp = call_ai(blueprint_prompt, history)
    thought, content = extract_thought(resp)
    print_box("RAGIONAMENTO ARCHITETTO", thought, Colors.GREY)
    
    files_to_create = extract_json_list(content)
    
    if not files_to_create:
        print(f"{Colors.FAIL}Errore: L'AI non ha generato una lista file valida. Uso fallback standard.{Colors.ENDC}")
        files_to_create = ["main.py", "requirements.txt", "README.md"]
    else:
        print(f"{Colors.GREEN}Blueprint Approvato: {files_to_create}{Colors.ENDC}")
        history.append({"role": "user", "content": blueprint_prompt})
        history.append({"role": "assistant", "content": json.dumps(files_to_create)})

    # --- FASE 2: COSTRUZIONE (LOOP DINAMICO) ---
    print(f"\n{Colors.HEADER}--- FASE 2: COSTRUZIONE ({len(files_to_create)} file) ---{Colors.ENDC}\n")

    for i, filename in enumerate(files_to_create):
        target_file = os.path.join(project_root, filename)
        
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        
        step_num = i + 1
        print(f"{Colors.BLUE}{Colors.BOLD}STEP {step_num}: Generazione {filename}...{Colors.ENDC}")
        
        code_prompt = f"""
        TASK: Scrivi il codice COMPLETO per il file '{filename}'.
        CONTESTO PROGETTO: {user_goal}
        STRUTTURA PREVISTA: {files_to_create}
        
        REGOLE:
        1. Inserisci SOLO il contenuto del file dentro un blocco markdown (```python, ```json, etc).
        2. Sii professionale. Includi commenti.
        """
        
        attempts = 0
        success = False
        while attempts < 3 and not success:
            full_resp = call_ai(code_prompt, history)
            thought, _ = extract_thought(full_resp)
            
            if attempts == 0:
                print_box(f"PENSIERO DEV ({filename})", thought, Colors.GREY)
            
            code = extract_code_block(full_resp)
            
            if code:
                with open(target_file, "w") as f:
                    f.write(code)
                print(f"{Colors.GREEN}✅ {filename} scritto.{Colors.ENDC}")
                history.append({"role": "user", "content": code_prompt})
                history.append({"role": "assistant", "content": f"Ho creato {filename}."})
                success = True
            else:
                print(f"{Colors.WARNING}⚠️ Codice non trovato. Riprovo...{Colors.ENDC}")
                code_prompt = f"ERRORE: Non hai messo il codice nel blocco ```. Riscrivi {filename}."
                attempts += 1
    
    print(f"\n{Colors.HEADER}--- PROGETTO COMPLETATO ---{Colors.ENDC}")
    print(f"Tutti i file sono in: {project_root}")
    
    if "main.py" in files_to_create:
        print(f"{Colors.CYAN}Per avviare: cd {project_root} && python3 main.py{Colors.ENDC}")
    elif "src/main.py" in files_to_create:
        print(f"{Colors.CYAN}Per avviare: cd {project_root} && python3 src/main.py{Colors.ENDC}")

if __name__ == "__main__":
    main()
