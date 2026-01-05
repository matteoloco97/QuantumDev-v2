# src/main.py

"""
Modulo principale dell'Engine di Raccolta Dati.

Questo modulo coordina l'esecuzione degli altri componenti:
- Scrape dati dal web con scraper.py
- Processa i dati con data_processor.py 
- Salva i risultati nel database con database.py
"""

# Importazioni necessarie
from src import scraper, data_processor, database

def get_data():
    """Ottiene i dati grezzi dal web."""
    return scraper.scrape_data()

def process_data(raw_data):
    """Processa i dati grezzi in un formato standardizzato."""
    return data_processor.process_data(raw_data)

def store_data(processed_data):
    """Salva i dati elaborati nel database."""
    database.store_data(processed_data)
    
def main():
    """Funzione di avvio dell'engine."""
    print("Starting Data Collection Engine...")
    raw_data = get_data()
    print(f"Raw data collected: {raw_data}")
    
    processed_data = process_data(raw_data)
    print(f"Processed data ready: {processed_data}")
    
    store_data(processed_data)
    print("Data stored successfully. Process completed.")

if __name__ == "__main__":
    main()