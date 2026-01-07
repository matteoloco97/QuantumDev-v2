import requests
from bs4 import BeautifulSoup
import json
import schedule
import time
import os
import logging
from datetime import datetime

# Configurazione del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

def extract_titles():
    try:
        # Fetch the webpage
        response = requests.get('https://www.ansa.it/')
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        titles = soup.find_all('h1', class_='title')
        
        # Read existing titles or create empty list if file doesn't exist
        try:
            with open('titles.json', 'r') as f:
                existing_titles = json.load(f)
        except FileNotFoundError:
            existing_titles = []
            
        # Extract and check for duplicates
        new_titles = []
        for idx, title in enumerate(titles):
            title_text = title.text.strip()
            if not any(t.get('title') == title_text for t in existing_titles):
                new_titles.append({'id': idx, 'title': title_text})
        
        # Combine and save to JSON
        all_titles = existing_titles + new_titles
        with open('titles.json', 'w') as f:
            json.dump(all_titles, f, indent=2)
            
        logging.info(f"Titles updated. Total titles: {len(all_titles)}")
        
    except Exception as e:
        logging.error(f"Error in extract_titles(): {str(e)}")

# Schedule the job
schedule.every(5).minutes.do(extract_titles)

# Start the scheduler
logging.info("Scraper started at: " + str(datetime.now()))
extract_titles()  # Initial run before the first schedule

while True:
    schedule.run_pending()
    time.sleep(1)