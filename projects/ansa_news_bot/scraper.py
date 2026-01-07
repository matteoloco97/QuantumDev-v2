import requests
from bs4 import BeautifulSoup
import json
import os
import time
import logging
from datetime import datetime

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# URL di ANSA e percorso del file JSON
URL = 'https://www.ansa.it/'
JSON_FILE = os.path.join(os.getcwd(), 'news_titles.json')

def main():
    try:
        # Fetch della pagina web
        response = requests.get(URL, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        # Parsing HTML con BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        titles = [element.text.strip() for element in soup.find_all(class_='title')]
        
        # Caricamento dei titoli esistenti dal file JSON
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'r') as f:
                existing_titles = set(json.load(f))
        else:
            existing_titles = set()
            
        # Controllo e salvataggio di nuovi titoli
        new_titles = []
        for title in titles:
            if title not in existing_titles:
                new_titles.append(title)
                existing_titles.add(title)
        
        if new_titles:
            logging.info(f"Nuovi titoli trovati: {len(new_titles)}")
            
            # Salvataggio su JSON con timestamp
            all_titles = list(existing_titles)
            with open(JSON_FILE, 'w') as f:
                json.dump(all_titles, f, indent=2)
        else:
            logging.info("Nessun nuovo titolo trovato.")
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Errore nel fetch: {e}")
    except Exception as e:
        logging.error(f"Errore generico: {e}")

if __name__ == "__main__":
    main()