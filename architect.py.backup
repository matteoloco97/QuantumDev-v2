import requests
import json
import os
import subprocess
import time
import sys
import re
import codecs

# --- CONFIGURAZIONE ---
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

def print_log(role, text, color=Colors.ENDC):
    print(f"{color}{Colors.BOLD}[{role}]{Colors.ENDC} {text}")

def ensure_project_dir(project_name):
    path = os.path.join(BASE_DIR, project_name)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

# --- CORE INTELLIGENCE ---

def extract_code_block(text):
    """
    Estrae il codice dai blocchi markdown. 
    È robusto: cerca python, bash, json o blocchi generici.
    🔧 FIX: Gestisce escape sequences letterali (\n → newline reale)
    """
    # Pattern 1: Blocco con linguaggio specificato
    match = re.search(r'```(?:\w+)?\n(.*?)```', text, re.DOTALL)
    if match:
        code = match.group(1).strip()
    else:
        # Pattern 2: Blocco senza newline immediato (caso raro ma possibile)
        match = re.search(r'```(.*?)```', text, re.DOTALL)
        if match:
            code = match.group(1).strip()
        else:
            return None
    
    # 🔧 FIX: Unescape se contiene literal escape sequences
    if '\\n' in code:
        real_newlines = code.count('\n')
        escaped_newlines = code.count('\\n')
        
        # Se >50% delle newline sono escaped, facciamo unescape
        if escaped_newlines > real_newlines * 0.5:
            try:
                code = codecs.decode(code, 'unicode_escape')
            except Exception:
                # Fallback manuale
                code = code.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
    
    return code

def extract_json_list(text):
    """Estrae una lista JSON in modo 'fuzzy' (cerca le parentesi quadre)."""
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
        # Timeout alto per scrittura codice
        resp = requests.post(API_URL, json=payload, timeout=300)
        data = resp.json()
        return data.get("response", "")
    except Exception as e:
        return f"ERRORE API: {e}"

# --- FASI DEL PROCESSO ---

def phase_1_blueprint(p_name, goal):
    """Definisce l'architettura."""
    print_log("ARCHITETTO", "Disegno blueprint...", Colors.CYAN)
    prompt = f"""
    SEI UN SOFTWARE ARCHITECT.
    PROGETTO: {p_name}
    OBIETTIVO: {goal}
    
    Elenca i file necessari in una lista JSON.
    Includi SEMPRE: main.py, requirements.txt, README.md.
    Rispondi SOLO con la lista JSON. Esempio: ["main.py", "utils.py"]
    """
    
    resp = call_ai(prompt)
    files = extract_json_list(resp)
    
    if not files:
        print_log("SYSTEM", "Blueprint confuso, uso standard fallback.", Colors.WARNING)
        return ["requirements.txt", "database.py", "scraper.py", "analyzer.py", "main.py", "README.md"]
    
    return files

def phase_2_construction(project_path, files, goal):
    """Genera i file con controllo 'Anti-Vuoto'."""
    print_log("COSTRUTTORE", "Avvio stesura codice...", Colors.CYAN)
    history = []
    
    for filename in files:
        file_path = os.path.join(project_path, filename)
        print(f"{Colors.BLUE}   Scrivo {filename}...{Colors.ENDC}", end="\r")
        
        prompt = f"""
        TASK: Scrivi il contenuto completo per '{filename}'.
        PROGETTO: {os.path.basename(project_path)}
        CONTESTO: {goal}
        
        REGOLE:
        1. Fornisci SOLO il codice all'interno di un blocco Markdown ```.
        2. Non aggiungere commenti fuori dal codice.
        3. Se è python, usa codice robusto e gestisci errori.
        """
        
        # RETRY LOOP (Anti-Empty File)
        attempts = 0
        success = False
        
        while attempts < 3:
            resp = call_ai(prompt, history)
            code = extract_code_block(resp)
            
            if code and len(code) > 10: # Minimo 10 caratteri per essere valido
                with open(file_path, "w") as f:
                    f.write(code)
                print(f"{Colors.GREEN}✅ {filename} salvato ({len(code)} bytes).     {Colors.ENDC}")
                history.append({"role": "user", "content": f"Codice per {filename}"})
                history.append({"role": "assistant", "content": "Fatto."})
                success = True
                break
            else:
                attempts += 1
                print(f"{Colors.WARNING}⚠️ {filename} vuoto o malformato (Tentativo {attempts}/3). Riprovo...{Colors.ENDC}")
                prompt += "\nIMPORTANTE: La tua risposta precedente non conteneva un blocco di codice valido. Riscrivilo interamente dentro ```."
        
        if not success:
            print(f"\n{Colors.FAIL}❌ ERRORE CRITICO: Impossibile generare {filename}. Stop.{Colors.ENDC}")
            return False # Blocca tutto se manca un file
            
    return True

def phase_3_runtime(project_path):
    """Esegue e ripara (Self-Healing senza JSON)."""
    print_log("RUNTIME", "Avvio main.py...", Colors.CYAN)
    
    # 1. Installazione Dipendenze
    if os.path.exists(os.path.join(project_path, "requirements.txt")):
        print_log("PIP", "Installazione dipendenze...", Colors.GREY)
        subprocess.run(["pip", "install", "-r", "requirements.txt"], cwd=project_path, capture_output=True)

    # 2. Execution Loop con Auto-Fix
    main_file = "main.py"
    max_retries = 3
    
    for attempt in range(max_retries):
        print(f"{Colors.WARNING}▶ Tentativo avvio {attempt+1}/{max_retries}...{Colors.ENDC}")
        
        res = subprocess.run(
            ["python3", main_file], 
            cwd=project_path, 
            capture_output=True, 
            text=True,
            timeout=30
        )
        
        if res.returncode == 0:
            print_log("SUCCESS", "Il software gira correttamente!", Colors.GREEN)
            print(f"\n{Colors.GREEN}{res.stdout[:1000]}{Colors.ENDC}")
            return
        
        # GESTIONE ERRORE
        error_msg = res.stderr
        print(f"{Colors.FAIL}❌ Crash rilevato:\n{error_msg[-500:]}{Colors.ENDC}")
        
        if attempt < max_retries - 1:
            print_log("MEDICO", "Analisi errore e patching...", Colors.CYAN)
            
            # Prompt di riparazione che chiede CODICE, non JSON
            fix_prompt = f"""
            HO RILEVATO UN ERRORE DURANTE L'ESECUZIONE DI {main_file}.
            
            ERRORE:
            {error_msg[-1000:]}
            
            TASK:
            Identifica quale file causa l'errore (spesso è main.py o un modulo importato).
            Riscrivi INTERAMENTE il codice corretto per quel file.
            
            FORMATO RISPOSTA:
            Nome del file nella prima riga (es: "database.py")
            Poi il blocco di codice markdown ```python ... ```
            """
            
            fix_resp = call_ai(fix_prompt)
            
            # Parsing "Grezzo" della risposta (Molto più robusto del JSON)
            lines = fix_resp.split('\n')
            target_file = None
            
            # Cerca un nome file probabile nelle prime righe
            for line in lines[:5]:
                if ".py" in line:
                    target_file = re.sub(r'[^\w\._-]', '', line).strip() # Pulisce caratteri strani
                    break
            
            new_code = extract_code_block(fix_resp)
            
            if target_file and new_code:
                full_path = os.path.join(project_path, target_file)
                with open(full_path, "w") as f:
                    f.write(new_code)
                print_log("MEDICO", f"Patch applicata a {target_file}.", Colors.GREEN)
            else:
                print_log("MEDICO", "Non sono riuscito a isolare il file o il codice per la patch.", Colors.FAIL)
                # Fallback: Riscrivi main.py se non si capisce
                if new_code:
                    with open(os.path.join(project_path, "main.py"), "w") as f:
                        f.write(new_code)
                    print_log("MEDICO", "Patch fallback applicata a main.py", Colors.WARNING)

    print_log("FAIL", "Impossibile avviare il software dopo i tentativi.", Colors.FAIL)

def main():
    os.system('clear')
    print(f"{Colors.HEADER}╔════════════════════════════════════════════╗")
    print(f"║      QUANTUM ARCHITECT V16 (Bulletproof)   ║")
    print(f"╚════════════════════════════════════════════╝{Colors.ENDC}")
    
    p_name = input("Nome Progetto: ").strip().replace(" ", "_")
    goal = input("Obiettivo: ")
    
    proj_dir = ensure_project_dir(p_name)
    
    # 1. Blueprint
    files = phase_1_blueprint(p_name, goal)
    print(f"Blueprint approvato: {files}")
    
    # 2. Costruzione (con stop on error)
    success = phase_2_construction(proj_dir, files, goal)
    if not success:
        print("Costruzione fallita. Interruzione.")
        return
        
    # 3. Runtime & Fixing
    phase_3_runtime(proj_dir)

if __name__ == "__main__":
    main()
