import requests
import json
import os
import sys
import re
import time
import glob
import codecs

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
    """
    Estrae codice da blocchi markdown, gestendo <think> tags di DeepSeek-R1.
    🔧 FIX: Gestisce escape sequences letterali (\n → newline reale)
    """
    # 1. Rimuovi <think> tags
    clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # 2. Estrai blocchi di codice
    matches = re.findall(r'```(?:\w+)?\s*(.*?)```', clean, re.DOTALL)
    if not matches:
        return None
    
    # 3. Prendi il blocco più lungo
    code = max(matches, key=len).strip()
    
    # 4. 🔧 FIX: Unescape se contiene literal escape sequences
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

def sanitize_filenames(files):
    """
    Clean and validate filenames.
    - Remove duplicates
    - Filter out library names
    - Ensure main.py and requirements.txt are present
    - Lowercase file extensions
    """
    LIBRARY_NAMES = {"requests", "json", "pandas", "numpy", "beautifulsoup4", "selenium", "bs4", "lxml"}
    
    cleaned = []
    seen = set()
    
    for f in files:
        # Normalize
        f = str(f).strip()
        if not f:
            continue
        
        # Skip libraries
        base_name = f.replace('.py', '').replace('.txt', '').replace('.md', '').replace('.json', '')
        if base_name.lower() in LIBRARY_NAMES:
            continue
        
        # Deduplicate
        if f in seen:
            continue
        seen.add(f)
        
        # Validate extension
        if any(f.endswith(ext) for ext in ['.py', '.txt', '.md', '.json', '.yml', '.yaml', '.toml', '.cfg']):
            cleaned.append(f)
    
    # Ensure essentials
    if "main.py" not in cleaned:
        cleaned.insert(0, "main.py")
    if "requirements.txt" not in cleaned:
        cleaned.append("requirements.txt")
    
    return cleaned

def extract_json_from_reasoning(text):
    """
    Ultra-robust JSON parser with multiple fallback strategies.
    Handles: pure JSON, numbered lists, bullet points, natural language.
    """
    # 1. Clean reasoning tags
    clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    clean = clean.replace("```json", "").replace("```", "").strip()
    
    # 2. Unescape if needed (like code blocks)
    if '\\n' in clean and clean.count('\\n') > clean.count('\n') * 0.5:
        try:
            clean = codecs.decode(clean, 'unicode_escape')
        except:
            pass
    
    # STRATEGY 1: Pure JSON array
    match = re.search(r'\[.*?\]', clean, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                files = [str(x) for x in parsed if isinstance(x, str)]
                if files:
                    return sanitize_filenames(files)
        except json.JSONDecodeError:
            pass
    
    # STRATEGY 2: JSON object with "files" key
    match = re.search(r'\{[^}]*"files"\s*:\s*\[.*?\][^}]*\}', clean, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(0))
            if 'files' in obj and isinstance(obj['files'], list):
                return sanitize_filenames(obj['files'])
        except json.JSONDecodeError:
            pass
    
    # STRATEGY 3: Numbered list (1. file.py\n2. file2.py)
    numbered = re.findall(r'^\s*\d+\.\s*(\S+\.(?:py|txt|md|json|yml|yaml|toml|cfg))', clean, re.MULTILINE | re.IGNORECASE)
    if numbered and len(numbered) >= 2:
        return sanitize_filenames(numbered)
    
    # STRATEGY 4: Bullet list (- file.py\n* file2.py)
    bullets = re.findall(r'^\s*[-*•]\s*(\S+\.(?:py|txt|md|json|yml|yaml|toml|cfg))', clean, re.MULTILINE | re.IGNORECASE)
    if bullets and len(bullets) >= 2:
        return sanitize_filenames(bullets)
    
    # STRATEGY 5: File pattern extraction (last resort)
    files = re.findall(r'\b(\w+\.(?:py|txt|md|json|yml|yaml|toml|cfg))\b', clean, re.IGNORECASE)
    if files:
        # Deduplicate preserving order
        seen = set()
        unique = []
        for f in files:
            if f not in seen and f not in ["requests", "json", "pandas", "numpy"]:  # Filter libraries
                seen.add(f)
                unique.append(f)
        
        if unique:
            return sanitize_filenames(unique)
    
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

def save_build_state(project_path, state):
    """Save build progress for crash recovery"""
    state_file = os.path.join(project_path, ".build_state.json")
    state['timestamp'] = time.time()
    
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

def load_build_state(project_path):
    """Load previous build state if exists"""
    state_file = os.path.join(project_path, ".build_state.json")
    
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            state = json.load(f)
        
        # Check if state is fresh (< 24h old)
        if time.time() - state.get('timestamp', 0) < 86400:
            return state
    
    return None

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
                    table = Table(title="✅ Blueprint Generato con Successo")
                    table.add_column("File", style="cyan")
                    table.add_column("Stato", style="green")
                    for f in files:
                        table.add_row(f, "⏳ In attesa di generazione")
                    console.print(table)
                    
                    return files
                
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

def generate_file_with_retry(filename, goal, research_context, history, max_attempts=3):
    """
    Generate file with intelligent retry logic.
    - Attempt 1: Standard prompt
    - Attempt 2: More explicit prompt with failure explanation
    - Attempt 3: Simplified version (MVP approach)
    """
    docker_constraints = """
    VINCOLI DOCKER (LINUX HEADLESS):
    1. No GUI.
    2. Selenium: usare --headless, --no-sandbox, --disable-dev-shm-usage.
    3. No subprocess.Popen() senza gestione corretta.
    """
    
    for attempt in range(max_attempts):
        # Build prompt based on attempt number
        if attempt == 0:
            # Standard prompt
            prompt = f"""
            TASK: Scrivi codice completo per '{filename}'.
            CONTESTO PROGETTO: {goal}
            {docker_constraints}
            {research_context}
            
            ISTRUZIONI DEEPSEEK-R1:
            1. Usa <think> per ragionare sull'implementazione
            2. DOPO </think>, scrivi SOLO il codice dentro ```python ... ```
            3. Codice robusto con try/except e logging
            4. No hardcoded paths assoluti, usa os.path
            """
        
        elif attempt == 1:
            # More explicit after failure
            prompt = f"""
            ⚠️ TENTATIVO {attempt + 1}/{max_attempts}
            
            Il tentativo precedente per '{filename}' ha fallito (codice vuoto o malformato).
            
            TASK: Scrivi codice VALIDO per '{filename}'.
            CONTESTO: {goal}
            
            REGOLE CRITICHE:
            1. USA <think> tags per ragionare
            2. DOPO </think>, scrivi ```python
            3. Poi il CODICE COMPLETO (minimo 30 righe)
            4. Chiudi con ```
            5. NON scrivere spiegazioni dopo il codice
            
            Esempio formato:
            <think>Per {filename} serve...</think>
            ```python
            import os
            
            def main():
                pass
            
            if __name__ == "__main__":
                main()
            ```
            """
        
        else:  # attempt == 2
            # Simplified MVP approach
            prompt = f"""
            ⚠️ ULTIMO TENTATIVO ({attempt + 1}/{max_attempts})
            
            Genera versione MINIMA FUNZIONANTE di '{filename}'.
            Obiettivo: {goal}
            
            FORMATO OBBLIGATORIO:
            <think>Logica minima necessaria</think>
            ```python
            # Codice minimo qui (anche solo 10 righe va bene)
            ```
            
            Concentrati su FUNZIONALITÀ BASE, ignora ottimizzazioni.
            """
        
        # Call AI
        resp = call_ai(prompt, history, mode="factory", silent=True)
        code = extract_code_block(resp)
        
        # Validation
        if code and len(code) > 20:
            # Additional validation for Python files
            if filename.endswith('.py'):
                try:
                    compile(code, filename, 'exec')
                    return code, attempt + 1  # Success
                except SyntaxError as e:
                    console.print(f"[warning]⚠️ Tentativo {attempt + 1}: Syntax error - {str(e)[:100]}[/warning]")
                    continue
            else:
                return code, attempt + 1  # Success for non-Python files
        
        # Log failure
        console.print(f"[warning]⚠️ Tentativo {attempt + 1}/{max_attempts} fallito per {filename}[/warning]")
    
    return None, max_attempts  # All attempts failed

def sh_phase_construction(project_path, files, goal, existing_state=None):
    console.print(Panel("[bold blue]FASE 2: RICERCA & SVILUPPO[/bold blue]", border_style="blue"))
    history = []
    
    # Track completed files for state persistence
    completed_files = set(existing_state.get('completed_files', [])) if existing_state else set()
    failed_files = []
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        main_task = progress.add_task("[cyan]Costruzione in corso...", total=len(files))
        
        for filename in files:
            if filename == "requirements.txt": 
                progress.advance(main_task)
                continue
            
            clean_filename = os.path.basename(filename)
            
            # Skip if already completed (resume functionality)
            if clean_filename in completed_files:
                console.print(f"[info]⏭️ {clean_filename} già completato (skip)[/info]")
                progress.advance(main_task)
                continue
            
            progress.update(main_task, description=f"[cyan]Lavorazione {clean_filename}...")
            real_path = os.path.join(project_path, clean_filename)
            
            # Research context
            research_context = ""
            if filename.endswith(".py"):
                search_query = f"python code example for {goal} related to {clean_filename} modern libraries headless"
                res = call_ai(f"USE [web_search] for: {search_query}", history, mode="factory", silent=True)
                if len(res) > 100 and "Traceback" not in res:
                    research_context = f"DATI RICERCA:\n{res[:2000]}\n"
            
            # Generate with retry
            code, attempts = generate_file_with_retry(clean_filename, goal, research_context, history)
            
            if code:
                with open(real_path, "w") as f:
                    f.write(code)
                console.print(f"[success]✅ {clean_filename} creato ({len(code)} bytes, {attempts} tentativi)[/success]")
                completed_files.add(clean_filename)
                
                # Save state checkpoint after each successful file
                save_build_state(project_path, {
                    'phase': 'construction_in_progress',
                    'blueprint': files,
                    'completed_files': list(completed_files),
                    'goal': goal
                })
                
                history.append({"role": "user", "content": f"Codice per {clean_filename} completato."})
                history.append({"role": "assistant", "content": "Confermato."})
            else:
                console.print(f"[error]❌ Impossibile generare {clean_filename} dopo {attempts} tentativi[/error]")
                failed_files.append(clean_filename)
                # Don't abort - continue with other files
            
            progress.advance(main_task)
    
    # Report summary
    if failed_files:
        console.print(f"[warning]⚠️ Build completato con {len(failed_files)} file falliti: {', '.join(failed_files)}[/warning]")
    
    return len(failed_files) == 0  # Return True only if all files succeeded

def validate_requirements(requirements_text):
    """
    Validate requirements.txt for known conflicts.
    Returns (is_valid, warnings, fixed_requirements)
    """
    KNOWN_CONFLICTS = {
        ('pandas', '>=2.0'): [('numpy', '<1.20', '>=1.20.0,<2.0.0')],
        ('tensorflow', '>=2.0'): [('numpy', '<1.19', '>=1.19.0,<2.0.0')],
    }
    
    warnings = []
    lines = [l.strip() for l in requirements_text.split('\n') if l.strip() and not l.startswith('#')]
    
    # Parse packages
    packages = {}
    for line in lines:
        match = re.match(r'([a-zA-Z0-9_-]+)([<>=!]+.*)?', line)
        if match:
            pkg_name = match.group(1).lower()
            version_spec = match.group(2) or ''
            packages[pkg_name] = {'spec': version_spec, 'line': line}
    
    # Check conflicts
    for (pkg1, ver1_spec), conflicts in KNOWN_CONFLICTS.items():
        if pkg1 in packages:
            pkg1_ver = packages[pkg1]['spec']
            if ver1_spec in pkg1_ver:
                for conflict_pkg, conflict_ver, suggested_fix in conflicts:
                    if conflict_pkg in packages:
                        pkg2_ver = packages[conflict_pkg]['spec']
                        if conflict_ver in pkg2_ver:
                            warnings.append(
                                f"⚠️ CONFLICT: {pkg1}{pkg1_ver} incompatible with {conflict_pkg}{pkg2_ver}\n"
                                f"   Suggested: {conflict_pkg}{suggested_fix}"
                            )
                            # Auto-fix - suggested_fix is just the version spec
                            packages[conflict_pkg]['line'] = f"{conflict_pkg}{suggested_fix}"
                            packages[conflict_pkg]['spec'] = suggested_fix
    
    # Rebuild requirements
    fixed_lines = [pkg['line'] for pkg in packages.values()]
    
    return (len(warnings) == 0, warnings, '\n'.join(fixed_lines))

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
        
        # Validate dependencies
        is_valid, warnings, fixed_req = validate_requirements(req)
        
        if not is_valid:
            console.print(Panel(
                '\n'.join(warnings),
                title="[yellow]⚠️ Dependency Conflicts Detected[/yellow]",
                border_style="yellow"
            ))
            
            if Confirm.ask("Applicare fix automatici?"):
                req = fixed_req
                console.print("[success]✅ Conflicts risolti automaticamente[/success]")
        
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
    
    # Check for existing build
    existing_state = load_build_state(path)
    files = None
    
    if existing_state:
        console.print(Panel(
            f"[yellow]🔄 Trovato build precedente interrotto:\n"
            f"Fase: {existing_state.get('phase', 'unknown')}\n"
            f"File completati: {len(existing_state.get('completed_files', []))}/{len(existing_state.get('blueprint', []))}\n"
            f"Timestamp: {time.ctime(existing_state.get('timestamp', 0))}[/yellow]",
            title="Resume Build?",
            border_style="yellow"
        ))
        
        if Confirm.ask("Vuoi riprendere da dove ti eri fermato?"):
            files = existing_state.get('blueprint', [])
            completed = set(existing_state.get('completed_files', []))
            goal = existing_state.get('goal', goal)
            
            console.print(f"[info]🔄 Resuming build... {len(completed)}/{len(files)} file già completati[/info]")
        else:
            state_file = os.path.join(path, ".build_state.json")
            if os.path.exists(state_file):
                os.remove(state_file)
            console.print("[info]Build precedente cancellato. Ricomincio da zero.[/info]")
            existing_state = None
    
    # Generate blueprint if not resuming
    if files is None:
        files = sh_phase_blueprint(p_name, goal)
        
        # Save initial state
        if files:
            save_build_state(path, {
                'phase': 'blueprint_complete',
                'blueprint': files,
                'completed_files': [],
                'goal': goal
            })
    
    if files:
        if sh_phase_construction(path, files, goal, existing_state):
            # Save state after construction
            save_build_state(path, {
                'phase': 'construction_complete',
                'blueprint': files,
                'completed_files': files,
                'goal': goal
            })
            
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
