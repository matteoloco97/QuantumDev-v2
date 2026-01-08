import os
import requests
import json
import subprocess
import shlex
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Security Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_WRITE_DIRS = ["projects/", "memories/"]
COMMAND_TIMEOUT = 60  # seconds
ALLOWED_COMMANDS = ["python3", "pip", "ls", "cat", "mkdir", "pytest"]

# --- TOOL 1: RICERCA WEB (Brave) ---
def web_search(query):
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key: return "ERRORE: BRAVE_API_KEY mancante nel file .env"
    try:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"X-Subscription-Token": api_key}
        params = {"q": query, "count": 3}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            results = resp.json().get('web', {}).get('results', [])
            if not results: return "Nessun risultato."
            output = f"--- RISULTATI WEB PER: '{query}' ---\n"
            for res in results:
                output += f"- {res.get('title')}: {res.get('url')}\n"
            return output
    except Exception as e: return f"Errore Web: {e}"
    return "Errore generico ricerca."

# --- TOOL 2: LETTORE DOCUMENTAZIONE ---
def read_url(url):
    try:
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200: return f"Errore: Status code {resp.status_code}"
        soup = BeautifulSoup(resp.text, 'html.parser')
        for script in soup(["script", "style", "nav", "footer"]): script.decompose()
        text = soup.get_text(separator='\n')
        lines = (line.strip() for line in text.splitlines())
        clean_text = '\n'.join(chunk for chunk in lines if chunk)
        return f"--- CONTENUTO URL: {url} ---\n{clean_text[:8000]}..."
    except Exception as e: return f"Errore lettura URL: {str(e)}"

# --- TOOL 3: SCRITTURA FILE ---
def write_file(filename, content):
    """
    Scrittura sicura con validazione path, size, atomic write.
    """
    try:
        # 1. Path validation
        clean_filename = os.path.normpath(filename)
        if clean_filename.startswith('..') or clean_filename.startswith('/'):
            return "ERRORE SICUREZZA: Path traversal detected"
        
        # 2. Directory whitelist
        if not any(clean_filename.startswith(d) for d in ALLOWED_WRITE_DIRS):
            return f"ERRORE SICUREZZA: Scrittura consentita solo in {ALLOWED_WRITE_DIRS}"
        
        # 3. Core file protection
        forbidden = ["core/", "engine.py", ".env", "Dockerfile"]
        if any(p in clean_filename for p in forbidden):
            return "ERRORE SICUREZZA: File di sistema protetto"
        
        # 4. Size limit
        if len(content) > MAX_FILE_SIZE:
            return f"ERRORE: File troppo grande (max {MAX_FILE_SIZE/1024/1024}MB)"
        
        # 5. Atomic write (temp → rename)
        base_path = os.getcwd()
        full_path = os.path.join(base_path, clean_filename)
        temp_path = full_path + ".tmp"
        
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        os.replace(temp_path, full_path)  # Atomic
        
        return f"✅ FILE SALVATO: {clean_filename} ({len(content)} bytes)"
    
    except Exception as e:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        return f"Errore scrittura: {str(e)}"

# --- TOOL 4: TERMINAL RUNNER (NUOVO - IL BRACCIO ESECUTIVO) ---
def terminal_run(command):
    """
    Esecuzione sicura con whitelist, timeout, sandboxing.
    """
    try:
        # 1. Safe parsing (no shell injection)
        try:
            parsed = shlex.split(command)
        except ValueError:
            return "ERRORE: Comando malformato"
        
        if not parsed:
            return "ERRORE: Comando vuoto"
        
        # 2. Whitelist enforcement - validate only the base command name
        base_cmd = os.path.basename(parsed[0])
        # Remove any path components to prevent bypass with /usr/bin/../../../bin/malicious
        if '/' in parsed[0] or '\\' in parsed[0]:
            return "ERRORE SICUREZZA: Path nel comando non consentito"
        
        if base_cmd not in ALLOWED_COMMANDS:
            return f"ERRORE SICUREZZA: '{base_cmd}' non consentito. Whitelist: {ALLOWED_COMMANDS}"
        
        # 3. Dangerous pattern detection
        dangerous = [';', '&&', '||', '|', '>', '<', '`', '$(', 'rm', 'wget', 'curl']
        full_cmd = ' '.join(parsed)
        if any(p in full_cmd for p in dangerous):
            return "ERRORE SICUREZZA: Pattern pericoloso rilevato"
        
        # 4. Working directory isolation
        safe_cwd = os.path.join(os.getcwd(), "projects")
        os.makedirs(safe_cwd, exist_ok=True)
        
        # 5. Execution with timeout
        result = subprocess.run(
            parsed,
            shell=False,  # ← CRITICAL: No shell injection
            cwd=safe_cwd,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT
        )
        
        output = result.stdout if result.returncode == 0 else result.stderr
        status = "✅" if result.returncode == 0 else f"❌ (exit {result.returncode})"
        
        return f"{status} OUTPUT:\n{output[:2000]}"
    
    except subprocess.TimeoutExpired:
        return f"ERRORE TIMEOUT: Comando superato {COMMAND_TIMEOUT}s"
    except FileNotFoundError:
        return f"ERRORE: Comando '{parsed[0]}' non trovato"
    except Exception as e:
        return f"Errore esecuzione: {str(e)}"

# Mappa dei tool disponibili
AVAILABLE_TOOLS = {
    "web_search": web_search,
    "read_url": read_url,
    "write_file": write_file,
    "terminal_run": terminal_run  # <--- REGISTRATO
}
