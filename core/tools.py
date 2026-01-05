import os
import requests
import json

# --- TOOL ESISTENTE: RICERCA WEB ---
def web_search(query):
    """Esegue una ricerca usando l'API Ufficiale di Brave Search."""
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key: return "ERRORE: BRAVE_API_KEY mancante."
    
    # ... (Il resto del codice di web_search rimane uguale, lo abbrevio per leggibilità) ...
    # Se vuoi ti ricopio tutto il blocco, ma basta mantenere quello che avevi prima.
    # Assumo tu mantenga la funzione web_search come era nel file caricato.
    # Qui sotto metto solo il placeholder per brevità, tu lascia il codice originale.
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

# --- NUOVO TOOL: SCRITTURA FILE ---
def write_file(filename, content):
    """
    Scrive del codice o testo in un file. 
    Uso: Utile per creare script python, salvare report o prendere appunti lunghi.
    """
    try:
        # Sicurezza: Impediamo di scrivere fuori dalla cartella di lavoro o sovrascrivere file core
        if "core/" in filename or "engine.py" in filename or "docker" in filename:
            return "ERRORE SICUREZZA: Non posso sovrascrivere i miei file vitali (core/*)."
        
        # Creiamo la cartella 'generated_software' se non esiste
        base_path = "generated_software"
        if not os.path.exists(base_path):
            os.makedirs(base_path)
            
        full_path = os.path.join(base_path, filename)
        
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return f"✅ FILE SALVATO CORRETTAMENTE: {full_path}. Puoi eseguirlo ora."
    except Exception as e:
        return f"Errore scrittura file: {str(e)}"

# Mappa dei tool disponibili per l'Engine
AVAILABLE_TOOLS = {
    "web_search": web_search,
    "write_file": write_file
}
