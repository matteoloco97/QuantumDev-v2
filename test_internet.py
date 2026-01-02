import sys
import os

# Patch percorsi
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'core'))

try:
    print("1. Importazione tools...")
    from core.tools import web_search
    
    print("2. Tentativo di connessione a DuckDuckGo...")
    query = "prezzo attuale bitcoin oggi"
    risultato = web_search(query)
    
    print("\n--- RISULTATO ---")
    print(str(risultato)[:200]) # Stampiamo i primi 200 caratteri
    print("-----------------")
    
    if "Errore" in str(risultato) or not risultato:
        print("❌ FALLITO: Il tool ha restituito un errore o è vuoto.")
    else:
        print("✅ SUCCESSO: Internet funziona e la libreria risponde.")

except Exception as e:
    print(f"\n❌ ERRORE CRITICO PYTHON: {e}")
