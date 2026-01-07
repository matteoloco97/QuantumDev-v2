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
    """Estrae codice da blocchi markdown, gestendo <think> tags di DeepSeek-R1"""
    clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    matches = re.findall(r'```(?:\w+)?\s*(.*?)```', clean, re.DOTALL)
    if matches: 
        return max(matches, key=len).strip()
    return None

def extract_json_from_reasoning(text):
    """Parser JSON ottimizzato per DeepSeek-R1"""
    clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    clean = clean.replace("```json", "").replace("```", "").strip()
    
    match = re.search(r'\[.*?\]', clean, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                return parsed
        except json.JSONDecodeError:
            pass
    
    py_files = re.findall(r'\b(\w+\.(?:py|txt|md|json))\b', clean)
    if py_files:
        return list(set(py_files))
    
    return None

def infer_files_from_goal(project_name, goal):
    """Inferisce file necessari da keywords nel goal"""
    base = ["main.py", "requirements.txt"]
    goal_lower = goal.lower()
    
    if any(k in goal_lower for k in ["scrap", "web", "html", "url", "sito", "pagina"]):
        base.extend(["scraper.py", "config.py"])
    
    if any(k in goal_lower for k in ["salva", "database", "sqlite", "json", "file", "csv"]):
        base.append("database.py")
    
    if any(k in goal_lower for k in ["bot", "telegram", "api", "webhook", "messaggio"]):
        base.extend(["bot.py", "handlers.py"])
    
    if any(k in goal_lower for k in ["loop", "minuti", "ore", "schedule", "periodico", "continuo"]):
        base.append("scheduler.py")
    
    if any(k in goal_lower for k in ["analisi", "calcolo", "statistiche", "report"]):
        base.append("analyzer.py")
    
    if len(base) > 3 and "utils.py" not in base:
        base.append("utils.py")
    
    console.print(f"[info]💡 Template inferito da keywords: {', '.join(base)}[/info]")
    return list(set(base))

def ensure_project_dir(project_name):
    path = os.path.join(BASE_DIR, project_name)
    if not os.path.exists(path): os.makedirs(path)
    return path

# ==============================================================================
# 2. SOFTWARE HOUSE ENGINE
# ==============================================================================

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
            
            REGOLE DEEPSEEK-R1:
            1. Usa <think> tags per il tuo reasoning interno
            2. DOPO </think>, rispondi SOLO a parole. Spiega l'approccio tecnico.
            3. NON generare codice o JSON in questa fase.
            4. Concludi chiedendo: "Posso procedere?"
            """
            
            resp = call_ai(user_input, history, system_context=system_prompt, mode="general")
            
            if extract_json_from_reasoning(resp):
                console.print("[warning]⚠️  L'Architetto ha violato il protocollo. Applicazione filtro correttivo...[/warning]")
                resp = call_ai("Hai generato strutture dati troppo presto. SPIEGA SOLO LA STRATEGIA A PAROLE, senza JSON o codice.", history, mode="general")
            
            console.print(Panel(Markdown(resp), title="[bold purple]Architetto[/bold purple]", border_style="purple"))
            
            user_input = Prompt.ask("[bold white]TU[/bold white]")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": resp})
            
            decision = call_ai(
                f"Analizza questa risposta: '{user_input}'. Se è una conferma (Si/Ok/Procedi/Va bene), rispondi APPROVED. Altrimenti rispondi DISCUSSION.", 
                mode="factory", 
                silent=True
            ).strip().upper()
            
            if "APPROVED" in decision:
                console.print("[success]✅ Strategia Approvata. Passaggio a generazione blueprint...[/success]")
                current_phase = "GENERATION"
            else:
                continue 

        if current_phase == "GENERATION":
            gen_prompt = f"""
            SEI UN ARCHITETTO SOFTWARE. PROGETTO: {p_name}
            OBIETTIVO: {initial_goal}
            
            TASK: Genera la lista dei file necessari.
            
            FORMATO DEEPSEEK-R1:
            1. Ragiona dentro <think>...</think> su quali file servono
            2. DOPO </think>, scrivi SOLO l'array JSON
            3. Formato: ["main.py", "scraper.py", "database.py", "requirements.txt"]
            
            Esempio di risposta corretta:
            <think>
            Per un web scraper che salva dati, servono:
            - main.py per orchestrare tutto
            - scraper.py per la logica di scraping
            - database.py per salvare i dati
            - config.py per le impostazioni
            - requirements.txt per le dipendenze
            </think>
            ["main.py", "scraper.py", "database.py", "config.py", "requirements.txt"]
            """
            
            max_attempts = 3
            for attempt in range(max_attempts):
                console.print(f"[info]🔄 Tentativo generazione blueprint {attempt+1}/{max_attempts}...[/info]")
                
                resp = call_ai(
                    "Genera l'array JSON dei file necessari ora.", 
                    history, 
                    system_context=gen_prompt, 
                    mode="factory"
                )
                
                console.print(f"[dim]Debug Response: {resp[:300]}...[/dim]")
                
                files = extract_json_from_reasoning(resp)
                
                if files and len(files) > 0:
                    sanitized_files = []
                    for item in files:
                        if isinstance(item, str):
                            if any(item.endswith(ext) for ext in ['.py', '.txt', '.md', '.json', '.yml']):
                                sanitized_files.append(item)
                        elif isinstance(item, dict):
                            for val in item.values():
                                if isinstance(val, str) and "." in val:
                                    sanitized_files.append(val)
                                    break
                    
                    sanitized_files = [
                        f for f in sanitized_files 
                        if f not in ["requests", "json", "pandas", "numpy", "beautifulsoup4"]
                    ]
                    
                    if "main.py" not in sanitized_files:
                        sanitized_files.insert(0, "main.py")
                    if "requirements.txt" not in sanitized_files:
                        sanitized_files.append("requirements.txt")
                    
                    table = Table(title="✅ Blueprint Generato con Successo")
                    table.add_column("File", style="cyan")
                    table.add_column("Stato", style="green")
                    for f in sanitized_files:
                        table.add_row(f, "⏳ In attesa di generazione")
                    console.print(table)
                    
                    return sanitized_files
                
                console.print(f"[warning]⚠️ Tentativo {attempt+1} fallito. Response non contiene JSON valido.[/warning]")
                
                if attempt < max_attempts - 1:
                    gen_prompt += f"\n\n⚠️ ATTENZIONE: Il tentativo {attempt+1} ha fallito. Assicurati di rispondere con un array JSON valido DOPO il tag </think>."
            
            console.print("[error]❌ Impossibile generare blueprint via AI. Uso template intelligente...[/error]")
            fallback_files = infer_files_from_goal(p_name, initial_goal)
            
            table = Table(title="📋 Blueprint Fallback (Template)")
            table.add_column("File", style="yellow")
            table.add_column("Fonte", style="dim")
            for f in fallback_files:
                table.add_row(f, "Inferito da keywords")
            console.print(table)
            
            return fallback_files

def sh_phase_construction(project_path, files, goal):
    console.print(Panel("[bold blue]FASE 2: RICERCA & SVILUPPO[/bold blue]", border_style="blue"))
    history = []
    
    docker_constraints = """
    VINCOLI DOCKER (LINUX HEADLESS):
    1. No GUI.
    2. Selenium: usare --headless, --no-sandbox, --disable-dev-shm-usage.
    3. No subprocess.Popen() senza gestione corretta.
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
                    research_context = f"DATI RICERCA:\n{res[:2000]}\n"
            
            prompt = f"""
            TASK: Scrivi codice completo per '{clean_filename}'.
            CONTESTO PROGETTO: {goal}
            {docker_constraints}
            {research_context}
            
            ISTRUZIONI DEEPSEEK-R1:
            1. Usa <think> per ragionare sull'implementazione
            2. DOPO </think>, scrivi SOLO il codice dentro ```python ... ```
            3. Codice robusto con try/except e logging
            4. No hardcoded paths assoluti, usa os.path
            """
            
            resp = call_ai(prompt, history, mode="factory", silent=True)
            code = extract_code_block(resp)
            
            if code and len(code) > 20:
                with open(real_path, "w") as f: 
                    f.write(code)
                console.print(f"[success]✅ {clean_filename} creato ({len(code)} bytes)[/success]")
            else:
                console.print(f"[error]❌ Fallita generazione {clean_filename}[/error]")
                return False
                
            history.append({"role": "user", "content": f"Codice per {clean_filename} completato."})
            history.append({"role": "assistant", "content": "Confermato."})
            progress.advance(main_task)
    
    return True

def sh_phase_integrator(project_path):
    console.print(Panel("[bold yellow]FASE 3: SYSTEM INTEGRATION[/bold yellow]", border_style="yellow"))
    
    with console.status("Analisi dipendenze incrociate...", spinner="bouncingBar"):
        py_files = glob.glob(os.path.join(project_path, "*.py"))
        all_code = ""
        for fpath in py_files:
            with open(fpath, "r") as f: 
                all_code += f"\n--- {os.path.basename(fpath)} ---\n" + f.read()
        
        prompt = f"""
        SEI UN SISTEMISTA. Analizza il codice e genera requirements.txt.
        
        CODICE:
        {all_code[:6000]}
        
        ISTRUZIONI:
        1. Identifica TUTTE le librerie importate
        2. Genera requirements.txt con versioni compatibili
        3. DOPO </think>, scrivi SOLO il contenuto del file (no markdown)
        """
        resp = call_ai(prompt, mode="factory", silent=True)
        
        req = extract_code_block(resp) or resp.replace("```", "").strip()
        req = re.sub(r'<think>.*?</think>', '', req, flags=re.DOTALL).strip()
        
        with open(os.path.join(project_path, "requirements.txt"), "w") as f: 
            f.write(req)
        
    console.print(f"[success]✅ requirements.txt sincronizzato.[/success]")
    console.print(Syntax(req, "text", theme="monokai", line_numbers=True))

def sh_phase_critic(project_path):
    console.print(Panel("[bold magenta]FASE 4: HOLISTIC CODE REVIEW[/bold magenta]", border_style="magenta"))
    
    with console.status("Scannerizzazione coerenza globale...", spinner="shark"):
        py_files = glob.glob(os.path.join(project_path, "*.py"))
        content = ""
        for f in py_files:
            with open(f, "r") as r: 
                content += f"\n=== {os.path.basename(f)} ===\n" + r.read()

        prompt = f"""
        REVIEWER OLISTICO. Controlla consistenza del codice:
        - Funzioni chiamate esistono?
        - Import corretti?
        - Logica coerente?
        
        CODICE: 
        {content[:8000]}
        
        Rispondi:
        - "OK" se tutto è coerente
        - Altrimenti, per ogni file da correggere: "FILE: nome.py" seguito da ```python codice corretto ```
        """
        resp = call_ai(prompt, mode="factory", silent=True)
    
    resp = re.sub(r'<think>.*?</think>', '', resp, flags=re.DOTALL)
    
    if "OK" in resp and len(resp) < 100:
        console.print("[success]✅ Nessun conflitto rilevato.[/success]")
    else:
        patches = re.split(r'FILE:\s*', resp)
        for patch in patches:
            if not patch.strip(): 
                continue
            lines = patch.split('\n')
            fname = lines[0].strip()
            code = extract_code_block(patch)
            if code and fname.endswith(".py"):
                with open(os.path.join(project_path, fname), "w") as f: 
                    f.write(code)
                console.print(f"[warning]🔧 {fname} patchato per consistenza.[/warning]")

def sh_phase_runtime(project_path, p_name, goal):
    console.print(Panel("[bold red]FASE 5: RUNTIME & AUTO-HEALING[/bold red]", border_style="red"))
    
    docker_p = os.path.join("projects", p_name)
    local_main = os.path.join(project_path, "main.py")
    venv = os.path.join(docker_p, "venv")
    
    with console.status("Setup ambiente isolato...", spinner="earth"):
        call_ai(f"TASK: Crea venv: python3 -m venv {venv}. Usa [TOOL: terminal_run, query: \"python3 -m venv {venv}\"]", mode="factory", silent=True)
        if os.path.exists(os.path.join(project_path, "requirements.txt")):
            call_ai(f"TASK: Install requirements in {venv}. Usa [TOOL: terminal_run, query: \"{venv}/bin/pip install -r {docker_p}/requirements.txt\"]", mode="factory", silent=True)

    cmd = f"{venv}/bin/python3 {docker_p}/main.py"
    
    for attempt in range(4):
        console.rule(f"[bold yellow]Test Run {attempt+1}/4[/bold yellow]")
        
        with console.status("Esecuzione script...", spinner="runner"):
            resp = call_ai(f"TASK: Esegui: {cmd}. Usa [TOOL: terminal_run, query: \"{cmd}\"]", mode="factory", silent=True)
        
        # 🔧 Pulisci formato tool dalla risposta prima di mostrare
        display_resp = re.sub(r'\[TOOL:.*?\].*?(?=\n\n|\n[A-Z]|$)', '', resp, flags=re.DOTALL).strip()
        if not display_resp or len(display_resp) < 10:
            display_resp = resp
        
        panel_color = "green" if "Traceback" not in display_resp else "red"
        console.print(Panel(display_resp[:500] + "..." if len(display_resp) > 500 else display_resp, 
                           title="Output Terminale", border_style=panel_color))
        
        if "Traceback" not in display_resp and "Error" not in display_resp:
            console.print("[bold green]🚀 SUCCESSO! Il sistema è stabile.[/bold green]")
            return
        
        console.print("[bold red]❌ Rilevato Crash. Applicazione protocollo medico...[/bold red]")
        with console.status("Applicazione Patch...", spinner="dots"):  # ✅ Fixed spinner
            fix = call_ai(f"DEBUGGER. OBIETTIVO: {goal}. ERRORE: {display_resp}. RISCRIVI main.py completo.", mode="factory", silent=True)
            code = extract_code_block(fix)
            if code:
                with open(local_main, "w") as f: 
                    f.write(code)
                console.print("[success]🔧 Patch applicata.[/success]")
            else:
                console.print("[error]⚠️ Impossibile generare patch.[/error]")

    console.print("[bold white on red] 💀 ABORTO DEFINITIVO. [/bold white on red]")
    diag = call_ai(f"Spiega errore fatale in ITALIANO: {display_resp}", history=[], mode="general", silent=True)
    console.print(Panel(Markdown(diag), title="Diagnosi Forense"))

# ==============================================================================
# 3. INTERFACES & MAIN
# ==============================================================================

def mode_general():
    print_header("QUANTUM GENERAL INTELLIGENCE", "DeepSeek-R1 Powered Analyst")
    history = load_session("general_brain")
    while True:
        u = Prompt.ask("[bold white]CEO[/bold white]")
        if u.lower() in ['exit', 'quit']: 
            break
        resp = call_ai(u, history, mode="general")
        console.print(Panel(Markdown(resp), title="Nexus", border_style="purple"))
        history.append({"role": "user", "content": u})
        history.append({"role": "assistant", "content": resp})
        save_session("general_brain", history)

def mode_factory():
    print_header("QUANTUM SOFTWARE FACTORY V5.2", "DeepSeek-R1 Optimized | Architect -> Build -> Integrate -> Critic -> Run")
    p_name = Prompt.ask("Nome Progetto").strip().replace(" ", "_")
    if not p_name: 
        return
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
        print_header("QUANTUM OS", "Neural Operating System - DeepSeek-R1 Edition")
        console.print("[1] 🧠 General Intelligence")
        console.print("[2] 🏭 Software Factory V5.2")
        console.print("[3] ❌ Exit")
        choice = Prompt.ask("Scelta", choices=["1", "2", "3"])
        if choice == "1": 
            mode_general()
        elif choice == "2": 
            mode_factory()
        elif choice == "3": 
            sys.exit()

if __name__ == "__main__":
    main()
