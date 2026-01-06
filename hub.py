import requests
import json
import os
import sys
import re

# --- CONFIGURAZIONE ---
API_URL = "http://localhost:8001/chat/god-mode"
BASE_DIR = "projects"
MEMORY_DIR = "memories"
MAX_HISTORY_LENGTH = 30

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

# ==============================================================================
# 1. CORE UTILITIES
# ==============================================================================

def call_ai(message, history=[], system_context="", mode="general"):
    """
    Invia richiesta all'Engine specificando la modalità.
    mode="general" -> Usa memoria, chatta.
    mode="factory" -> Niente memoria, solo esecuzione.
    """
    full_prompt = f"{system_context}\n\nUTENTE: {message}" if system_context else message
    payload = {
        "message": full_prompt, 
        "history": history,
        "mode": mode 
    }
    try:
        resp = requests.post(API_URL, json=payload, timeout=300)
        return resp.json().get("response", "")
    except Exception as e: return f"ERRORE API: {e}"

def load_session(name):
    path = os.path.join(MEMORY_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path, 'r') as f: return json.load(f)
    return []

def save_session(name, history):
    if not os.path.exists(MEMORY_DIR): os.makedirs(MEMORY_DIR)
    if len(history) > MAX_HISTORY_LENGTH:
        history = history[-MAX_HISTORY_LENGTH:]
    path = os.path.join(MEMORY_DIR, f"{name}.json")
    with open(path, 'w') as f: json.dump(history, f, indent=2)

def extract_code_block(text):
    matches = re.findall(r'```(?:\w+)?\s*(.*?)```', text, re.DOTALL)
    if matches: return max(matches, key=len).strip()
    return None

def extract_json_list(text):
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match: return json.loads(match.group(0))
    except: pass
    return None

# ==============================================================================
# 2. SOFTWARE HOUSE ENGINE (FACTORY MODE)
# ==============================================================================

def ensure_project_dir(project_name):
    path = os.path.join(BASE_DIR, project_name)
    if not os.path.exists(path): os.makedirs(path)
    return path

def sh_phase_blueprint(p_name, goal):
    print(f"{Colors.CYAN}[ARCHITETTO] Disegno blueprint...{Colors.ENDC}")
    # Qui usiamo mode="general" perché serve creatività e memoria storica
    prompt = f"SEI UN ARCHITETTO SOFTWARE.\nPROGETTO: {p_name}\nOBIETTIVO: {goal}\nRestituisci SOLO una lista JSON dei file necessari."
    resp = call_ai(prompt, mode="general") 
    files = extract_json_list(resp)
    
    cleaned_files = []
    if isinstance(files, list):
        for item in files:
            if isinstance(item, str): cleaned_files.append(item)
            elif isinstance(item, dict):
                for key in ['file', 'filename', 'name', 'path']:
                    if key in item:
                        cleaned_files.append(item[key])
                        break
    if not cleaned_files: return ["main.py", "requirements.txt", "README.md"]
    return cleaned_files

def sh_phase_construction(project_path, files, goal):
    print(f"{Colors.CYAN}[COSTRUTTORE] Avvio stesura codice...{Colors.ENDC}")
    history = []
    
    for filename in files:
        clean_filename = os.path.basename(filename) 
        print(f"{Colors.BLUE}   Scrivo {clean_filename}...{Colors.ENDC}", end="\r")
        rel_path = os.path.join(os.path.basename(project_path), clean_filename)
        
        prompt = f"""
        TASK: Scrivi il codice per '{clean_filename}'.
        CONTESTO: {goal}
        OPZIONE A: Usa [TOOL: write_file].
        OPZIONE B: Scrivi codice in ```python ... ```.
        """
        # QUI USIAMO FACTORY MODE: Niente chiacchiere, niente memoria vecchia
        resp = call_ai(prompt, history, mode="factory")
        real_path = os.path.join(project_path, clean_filename)
        
        if os.path.exists(real_path):
             print(f"{Colors.GREEN}✅ {clean_filename} creato (Tool).        {Colors.ENDC}")
        else:
             code = extract_code_block(resp)
             if code:
                 with open(real_path, "w") as f: f.write(code)
                 print(f"{Colors.GREEN}✅ {clean_filename} creato (Hub).         {Colors.ENDC}")
             else:
                 print(f"\n{Colors.FAIL}❌ Errore su {clean_filename}.{Colors.ENDC}")
                 return False
        history.append({"role": "user", "content": f"File {clean_filename} salvato."})
        history.append({"role": "assistant", "content": "Ok."})
    return True

def sh_phase_runtime(project_path, p_name):
    print(f"{Colors.CYAN}[RUNTIME] Avvio test remoto (Docker)...{Colors.ENDC}")
    docker_project_path = os.path.join("projects", p_name)
    
    # 1. Installazione
    if os.path.exists(os.path.join(project_path, "requirements.txt")):
        print(f"{Colors.GREY}Richiesta installazione dipendenze...{Colors.ENDC}")
        install_cmd = f"pip install -r {docker_project_path}/requirements.txt"
        
        prompt = f"""
        TASK: Esegui comando shell.
        CMD: {install_cmd}
        ESEMPIO RISPOSTA: [TOOL: terminal_run, query: "{install_cmd}"]
        """
        call_ai(prompt, mode="factory")

    # 2. Esecuzione
    main_cmd = f"python3 {docker_project_path}/main.py"
    
    for attempt in range(3):
        print(f"{Colors.WARNING}▶ Test Run {attempt+1}...{Colors.ENDC}")
        
        prompt = f"""
        TASK: Esegui script.
        CMD: {main_cmd}
        ESEMPIO RISPOSTA: [TOOL: terminal_run, query: "{main_cmd}"]
        """
        
        # FACTORY MODE ATTIVA
        resp = call_ai(prompt, mode="factory")
        print(f"\n{Colors.BLUE}REPORT ENGINE:{Colors.ENDC}\n{resp}\n")
        
        if "$" in resp or "Bitcoin" in resp or "price" in resp: 
            print(f"{Colors.GREEN}✅ SUCCESSO! Output ricevuto.{Colors.ENDC}")
            return
        
        if "Traceback" in resp:
             print(f"{Colors.FAIL}Errore codice. Riprovo...{Colors.ENDC}")

# ==============================================================================
# 3. INTERFACES
# ==============================================================================

def mode_general_hub():
    os.system('clear')
    print(f"{Colors.HEADER}╔════════════════════════════════════════════════════╗")
    print(f"║          QUANTUM GENERAL INTELLIGENCE              ║")
    print(f"╚════════════════════════════════════════════════════╝{Colors.ENDC}")
    session_name = "general_brain"
    history = load_session(session_name)
    while True:
        try:
            user_input = input(f"{Colors.BOLD}CEO > {Colors.ENDC}").strip()
            if user_input.lower() in ['exit', 'quit', 'menu']: break
            print(f"{Colors.CYAN}Nexus pensa...{Colors.ENDC}", end="\r")
            # GENERAL MODE: Qui usiamo la memoria
            resp = call_ai(user_input, history, mode="general")
            print(f"\n{Colors.BLUE}NEXUS >{Colors.ENDC} {resp}\n")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": resp})
            save_session(session_name, history)
        except KeyboardInterrupt: break

def mode_software_house():
    os.system('clear')
    print(f"{Colors.HEADER}╔════════════════════════════════════════════════════╗")
    print(f"║            QUANTUM SOFTWARE FACTORY                ║")
    print(f"╚════════════════════════════════════════════════════╝{Colors.ENDC}")
    p_name = input("Nome Progetto (es. betting_bot): ").strip().replace(" ", "_")
    if not p_name: return
    goal = input("Obiettivo Tecnico: ").strip()
    path = ensure_project_dir(p_name)
    
    files = sh_phase_blueprint(p_name, goal) # Qui usa GENERAL
    print(f"{Colors.GREEN}Blueprint: {files}{Colors.ENDC}")
    
    if input("Procedere? (S/n): ").lower() != 'n':
        if sh_phase_construction(path, files, goal): # Qui usa FACTORY
            sh_phase_runtime(path, p_name) # Qui usa FACTORY
    
    input("\nPremi INVIO per tornare al menu...")

def main():
    while True:
        os.system('clear')
        print(f"{Colors.HEADER}╔════════════════════════════════════════════╗")
        print(f"║         QUANTUM OS - MAIN MENU             ║")
        print(f"╚════════════════════════════════════════════╝{Colors.ENDC}")
        print("1. 🧠 GENERAL INTELLIGENCE (Gemini Mode)")
        print("2. 🏭 SOFTWARE HOUSE (Builder Mode)")
        print("3. ❌ ESCI")
        choice = input("\nScelta > ")
        if choice == "1": mode_general_hub()
        elif choice == "2": mode_software_house()
        elif choice == "3": sys.exit()

if __name__ == "__main__":
    main()
