import os
import requests
import json

def web_search(query):
    """
    Esegue una ricerca usando l'API Ufficiale di Brave Search.
    """
    api_key = os.getenv("BRAVE_API_KEY")
    
    if not api_key:
        return "ERRORE CRITICO: BRAVE_API_KEY non trovata nelle variabili d'ambiente."

    print(f"DEBUG: Brave API Search per: {query}")
    
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "X-Subscription-Token": api_key,
        "Accept": "application/json"
    }
    params = {
        "q": query,
        "count": 3
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('web', {}).get('results', [])
            
            if not results:
                return "Nessun risultato trovato."

            output = f"--- RISULTATI BRAVE PER: '{query}' ---\n"
            for i, res in enumerate(results, 1):
                title = res.get('title', 'No Title')
                link = res.get('url', 'No Link')
                desc = res.get('description', 'No Description')
                
                output += f"{i}. TITOLO: {title}\n"
                output += f"   LINK: {link}\n"
                output += f"   DESCRIZIONE: {desc}\n\n"
            
            return output
        elif response.status_code == 429:
            return "Errore: Limite richieste API raggiunto (Rate Limit)."
        else:
            return f"Errore API Brave: {response.status_code} - {response.text}"

    except Exception as e:
        return f"ERRORE CONNESSIONE: {str(e)}"

AVAILABLE_TOOLS = {
    "web_search": web_search
}
