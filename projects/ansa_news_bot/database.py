import json
import os

def load_titles():
    try:
        with open('ansa_titles.json', 'r') as f:
            titles = json.load(f)
            return titles if isinstance(titles, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_titles(titles):
    try:
        with open('ansa_titles.json', 'w') as f:
            json.dump(titles, f)
    except Exception as e:
        print(f"Errore nel salvataggio: {e}")

def add_new_titles(new_titles):
    current_titles = load_titles()
    combined = current_titles + new_titles
    unique = list(set(combined))
    save_titles(unique)

def reset_db():
    titles = load_titles()
    if len(titles) > 1000:
        titles = titles[-1000:]
        save_titles(titles)