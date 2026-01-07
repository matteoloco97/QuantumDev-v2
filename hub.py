import requests
import json
import os
import sys
import re
import time
import glob

# --- CHECK DIPENDENZE GRAFICHE ---
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Prompt, Confirm
    from rich.theme import Theme
except ImportError:
    print("ERRORE: Manca la libreria 'rich'.")
    print("Esegui: pip install rich")
    sys.exit(1)

# --- CONFIGURAZIONE UI ---
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "ai": "bold purple",
    "user": "bold white",
})
console = Console(theme=custom_theme)

# --- CONFIGURAZIONE SISTEMA ---
API_URL = "http://localhost:8001/chat/god-mode"
BASE_DIR = "projects"
MEMORY_DIR = "memories"
MAX_HISTORY_LENGTH = 30

# ==============================================================================
# 1. CORE UTILITIES
# ==============================================================================

def print_header(title, subtitle=""):
    console.clear()
    console.print(Panel(
        f"[bold white]{subtitle}[/bold white]", 
        title=f"[bold magenta]{title}[/bold magenta]", 
        border_style="purple",
        padding=(1, 2)
    ))

def call_ai(message, history=[], system_context="", mode="general", silent=False):
    full_prompt = f"{system_context}\n\nUTENTE: {message}" if system_context else message
    payload = {
        "message": full_prompt, 
        "history": history,
        "mode": mode 
    }
    
    if not silent:
        with console.status("[ai]Elaborazione neurale in corso...", spinner="dots"):
            try:
                resp = requests.post(API_URL, json=payload, timeout=300)
                text = resp.json().get("response", "")
                return text
            except Exception as e: return f"ERRORE API: {e}"
    else:
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

def ensure_project_dir(project_name):
    path = os.path.join(BASE_DIR, project_name)
    if not os.path.exists(path): os.makedirs(path)
    return path

# ==============================================================================
# 2. SOFTWARE HOUSE ENGINE (FACTORY V5.1 - BUGFIXED)
# ==============================================================================

# --- FASE 1: ARCHITETTO (Con Sanitizer) ---
def sh_phase_blueprint(p_name, initial_goal):
    console.print(Panel("[bold cyan]FASE 1: STRATEGIA & ARCHITETTURA[/bold cyan]", border_style="cyan"))
    
    history = []
    user_input = initial_goal
    current_phase = "CONSULTATION" 
    
    while True:
        if current_phase == "CONSULTATION":
            system_prompt = f"""
            SEI UN SENIOR TECH LEAD. PROGETTO: {p_name}
            OBIETTIVO: Discutere la strategia tecnica.
            REGOLE:
            1. Rispondi SOLO a parole. Spiega l'approccio tecnico.
            2. NON generare codice o JSON.
            3. Concludi chiedendo: "Posso procedere?"
            """
            
            resp = call_ai(user_input, history, system_context=system_prompt, mode="general")
            
            if extract_json_list(resp):
                console.print("[warning]⚠️  L'Architetto ha violato il protocollo. Applicazione filtro correttivo...[/warning]")
                resp = call_ai("Hai generato file troppo presto. SPIEGA SOLO LA STRATEGIA A PAROLE.", history, mode="general")
            
            console.print(Panel(Markdown(resp), title="[bold purple]Architetto[/bold purple]", border_style="purple"))
            
            user_input = Prompt.ask("[bold white]TU[/bold white]")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": resp})
            
            decision = call_ai(f"Analizza: '{user_input}'. Se conferma (Si/Ok/Procedi) rispondi APPROVED, altrimenti DISCUSSION.", mode="factory", silent=True).strip().upper()
            
            if "APPROVED" in decision:
                console.print("[success]✅ Strategia Approvata.[/success]")
                current_phase = "GENERATION"
            else:
                continue 

        if current_phase == "GENERATION":
            gen_prompt = f"""
            SEI UN ARCHITETTO SOFTWARE. PROGETTO: {p_name}
            Piano approvato. TASK: Genera SOLO la lista JSON dei file (incluso main.py).
            """
            resp = call_ai("Genera il blueprint JSON ora.", history, system_context=gen_prompt, mode="general")
            files = extract_json_list(resp)
            
            if files:
                # --- FIX CRITICO: SANITIZZAZIONE LISTA ---
                # L'AI a volte restituisce [{"filename": "main.py"}] invece di ["main.py"]
                sanitized_files = []
                for item in files:
                    if isinstance(item, str):
                        sanitized_files.append(item)
                    elif isinstance(item, dict):
                        # Cerca il primo valore stringa utile nel dizionario
                        for val in item.values():
                            if isinstance(val, str) and "." in val:
                                sanitized_files.append(val)
                                break
                
                # Pulizia finale
                files = [f for f in sanitized_files if f not in ["requests", "json", "pandas"] and isinstance(f, str)]
                if "main.py" not in files: files.insert(0, "main.py")
                # -----------------------------------------

                # Ora è sicuro stampare
                table = Table(title="Blueprint Generato")
                table.add_column("File", style="cyan")
                table.add_column("Stato", style="green")
                for f in files: table.add_row(f, "In attesa")
                console.print(table)
                
                return files
            else:
                console.print("[error]❌ Errore generazione JSON. Riprovo...[/error]")
                continue 

# --- FASE 2: COSTRUTTORE ---
def sh_phase_construction(project_path, files, goal):
    console.print(Panel("[bold blue]FASE 2: RICERCA & SVILUPPO[/bold blue]", border_style="blue"))
    history = []
    
    docker_constraints = """
    VINCOLI DOCKER (LINUX HEADLESS):
    1. No GUI.
    2. Selenium: usare --headless, --no-sandbox, --disable-dev-shm-usage.
    """
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        main_task = progress.add_task("[cyan]Costruzione in corso...", total=len(files))
        
        for filename in files:
            if filename == "requirements.txt": 
                progress.advance(main_task)
                continue
            
            clean_filename = os.path.basename(filename)
            progress.update(main_task, description=f"[cyan]Lavorazione {clean_filename}...")
            real_path = os.path.join(project_path, clean_filename)
            
            research_context = ""
            if filename.endswith(".py"):
                search_query = f"python code example for {goal} related to {clean_filename} modern libraries headless"
                res = call_ai(f"USE [web_search] for: {search_query}", history, mode="factory", silent=True)
                if len(res) > 100 and "Traceback" not in res:
                    research_context = f"DATI RICERCA:\n{res}\n"
            
            prompt = f"""
            TASK: Scrivi codice per '{clean_filename}'.
            CONTESTO: {goal}
            {docker_constraints}
            {research_context}
            ISTRUZIONI: Restituisci SOLO codice ```python ... ```.
            """
            
            resp = call_ai(prompt, history, mode="factory", silent=True)
            code = extract_code_block(resp)
            
            if code:
                with open(real_path, "w") as f: f.write(code)
                console.print(f"[success]✅ {clean_filename} creato.[/success]")
            else:
                console.print(f"[error]❌ Fallita generazione {clean_filename}[/error]")
                return False
                
            history.append({"role": "user", "content": f"{clean_filename} fatto."})
            history.append({"role": "assistant", "content": "Ok."})
            progress.advance(main_task)
            
    return True

# --- FASE 3: INTEGRATORE ---
def sh_phase_integrator(project_path):
    console.print(Panel("[bold yellow]FASE 3: SYSTEM INTEGRATION[/bold yellow]", border_style="yellow"))
    
    with console.status("Analisi dipendenze incrociate...", spinner="bouncingBar"):
        py_files = glob.glob(os.path.join(project_path, "*.py"))
        all_code = ""
        for fpath in py_files:
            with open(fpath, "r") as f: all_code += f"\n--- {os.path.basename(fpath)} ---\n" + f.read()
        
        prompt = f"""
        SEI UN SISTEMISTA. Analizza il codice:
        {all_code[:6000]}
        Genera 'requirements.txt' corretto. SOLO TESTO.
        """
        resp = call_ai(prompt, mode="factory", silent=True)
        req = extract_code_block(resp) or resp.replace("```", "").strip()
        
        with open(os.path.join(project_path, "requirements.txt"), "w") as f: f.write(req)
        
    console.print(f"[success]✅ requirements.txt sincronizzato.[/success]")
    console.print(Syntax(req, "text", theme="monokai", line_numbers=True))

# --- FASE 4: CRITICO OLISTICO ---
def sh_phase_critic(project_path):
    console.print(Panel("[bold magenta]FASE 4: OLISTIC CODE REVIEW[/bold magenta]", border_style="magenta"))
    
    with console.status("Scannerizzazione coerenza globale...", spinner="shark"):
        py_files = glob.glob(os.path.join(project_path, "*.py"))
        content = ""
        for f in py_files:
            with open(f, "r") as r: content += f"\n=== {os.path.basename(f)} ===\n" + r.read()

        prompt = f"""
        REVIEWER OLISTICO. Controlla consistenza (funzioni chiamate esistono?).
        CODICE: {content[:8000]}
        Rispondi OK o correggi con formato: FILE: nome\n```python...```
        """
        resp = call_ai(prompt, mode="factory", silent=True)
    
    if "OK" in resp and len(resp) < 100:
        console.print("[success]✅ Nessun conflitto rilevato.[/success]")
    else:
        patches = re.split(r'FILE:\s*', resp)
        for patch in patches:
            if not patch.strip(): continue
            lines = patch.split('\n')
            fname = lines[0].strip()
            code = extract_code_block(patch)
            if code and fname.endswith(".py"):
                with open(os.path.join(project_path, fname), "w") as f: f.write(code)
                console.print(f"[warning]🔧 {fname} patchato per consistenza.[/warning]")

# --- FASE 5: RUNTIME ---
def sh_phase_runtime(project_path, p_name, goal):
    console.print(Panel("[bold red]FASE 5: RUNTIME & AUTO-HEALING[/bold red]", border_style="red"))
    
    docker_p = os.path.join("projects", p_name)
    local_main = os.path.join(project_path, "main.py")
    venv = os.path.join(docker_p, "venv")
    
    with console.status("Setup ambiente isolato...", spinner="earth"):
        call_ai(f"TASK: Crea venv: python3 -m venv {venv}. Usa [TOOL: terminal_run].", mode="factory", silent=True)
        if os.path.exists(os.path.join(project_path, "requirements.txt")):
            call_ai(f"TASK: Install requirements in {venv}. Usa [TOOL: terminal_run].", mode="factory", silent=True)

    cmd = f"{venv}/bin/python3 {docker_p}/main.py"
    
    for attempt in range(4):
        console.rule(f"[bold yellow]Test Run {attempt+1}/4[/bold yellow]")
        
        with console.status("Esecuzione script...", spinner="runner"):
            resp = call_ai(f"TASK: Esegui: {cmd}. Usa [TOOL: terminal_run].", mode="factory", silent=True)
        
        panel_color = "green" if "Traceback" not in resp else "red"
        console.print(Panel(resp[:500] + "...", title="Output Terminale", border_style=panel_color))
        
        if "Traceback" not in resp and "Error" not in resp and ("Done" in resp or "{" in resp or "$" in resp):
            console.print("[bold green]🚀 SUCCESSO! Il sistema è stabile.[/bold green]")
            return
        
        console.print("[bold red]❌ Rilevato Crash. Applicazione protocollo medico...[/bold red]")
        with console.status("Applicazione Patch...", spinner="medical"):
            fix = call_ai(f"DEBUGGER. OBIETTIVO: {goal}. ERRORE: {resp}. RISCRIVI main.py.", mode="factory", silent=True)
            code = extract_code_block(fix)
            if code:
                with open(local_main, "w") as f: f.write(code)
                console.print("[success]🔧 Patch applicata.[/success]")
            else:
                console.print("[error]⚠️ Impossibile generare patch.[/error]")

    console.print("[bold white on red] 💀 ABORTO DEFINITIVO. [/bold white on red]")
    diag = call_ai(f"Spiega errore fatale in ITALIANO: {resp}", history=[], mode="general", silent=True)
    console.print(Panel(Markdown(diag), title="Diagnosi Forense"))

# ==============================================================================
# 3. INTERFACES & MAIN
# ==============================================================================

def mode_general():
    print_header("QUANTUM GENERAL INTELLIGENCE", "Gemini-Powered Analyst")
    history = load_session("general_brain")
    while True:
        u = Prompt.ask("[bold white]CEO[/bold white]")
        if u.lower() in ['exit', 'quit']: break
        resp = call_ai(u, history, mode="general")
        console.print(Panel(Markdown(resp), title="Nexus", border_style="purple"))
        history.append({"role": "user", "content": u})
        history.append({"role": "assistant", "content": resp})
        save_session("general_brain", history)

def mode_factory():
    print_header("QUANTUM SOFTWARE FACTORY V5.1", "Architect -> Build -> Integrate -> Critic -> Run")
    p_name = Prompt.ask("Nome Progetto").strip().replace(" ", "_")
    if not p_name: return
    goal = Prompt.ask("Obiettivo")
    path = ensure_project_dir(p_name)
    
    files = sh_phase_blueprint(p_name, goal)
    if files:
        if sh_phase_construction(path, files, goal):
            sh_phase_integrator(path)
            sh_phase_critic(path)
            sh_phase_runtime(path, p_name, goal)
    
    Prompt.ask("\nPremi INVIO per tornare al menu...")

def main():
    while True:
        print_header("QUANTUM OS", "Neural Operating System")
        console.print("[1] 🧠 General Intelligence")
        console.print("[2] 🏭 Software Factory V5.1")
        console.print("[3] ❌ Exit")
        choice = Prompt.ask("Scelta", choices=["1", "2", "3"])
        if choice == "1": mode_general()
        elif choice == "2": mode_factory()
        elif choice == "3": sys.exit()

if __name__ == "__main__":
    main()
