import requests
from bs4 import BeautifulSoup
import json
import os
from config import URL, HEADERS


def scrape_website(url=URL):
    """Funzione che effettua lo scraping di una pagina web."""
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup
    except requests.exceptions.RequestException as e:
        print(f"Errore durante lo scraping: {e}")
        return None


def extract_data(soup):
    """Estrae i dati necessari dallo soup."""
    items = []
    for item in soup.find_all('div', class_='item'):
        name = item.find('h3').text.strip()
        price = item.find('p', class_='price').text.strip()
        items.append({'name': name, 'price': price})
    return items


def save_data(data):
    """Salva i dati in un file JSON nella directory data/raw."""
    filename = os.path.join('data', 'raw', 'scraped_data.json')
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)