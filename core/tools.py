import os
import requests
import json
import subprocess
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

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
    try:
        if "core/" in filename or "engine.py" in filename:
            return "ERRORE SICUREZZA: Accesso negato ai file core."
        base_path = os.getcwd()
        full_path = os.path.join(base_path, filename)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ FILE SALVATO: {filename}"
    except Exception as e: return f"Errore scrittura file: {str(e)}"

# --- TOOL 4: TERMINAL RUNNER (NUOVO - IL BRACCIO ESECUTIVO) ---
def terminal_run(command):
    """
    Esegue comandi shell all'interno del container Docker.
    È qui che avviene la magia dell'esecuzione isolata.
    """
    try:
        # Security: Blocchiamo comandi distruttivi
        forbidden = ["rm -rf /", ":(){ :|:& };:", "wget", "curl"] 
        if any(bad in command for bad in forbidden):
            return "ERRORE SICUREZZA: Comando non consentito."

        # Eseguiamo il comando con timeout di 60 secondi
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=60,
            cwd=os.getcwd() # Esegue nella root del container (/app)
        )
        
        output = result.stdout
        errors = result.stderr
        
        if result.returncode == 0:
            return f"✅ SUCCESS:\n{output}"
        else:
            return f"❌ ERROR (Code {result.returncode}):\n{output}\n{errors}"
            
    except subprocess.TimeoutExpired:
        return "❌ TIMEOUT: Il processo ha impiegato più di 60 secondi."
    except Exception as e:
        return f"❌ ERRORE EXEC: {str(e)}"

# Mappa dei tool disponibili
AVAILABLE_TOOLS = {
    "web_search": web_search,
    "read_url": read_url,
    "write_file": write_file,
    "terminal_run": terminal_run  # <--- REGISTRATO
}
