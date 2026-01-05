from database import save_match, get_all_matches
from scraper import scrape_data
from analyzer import analyze_opportunities
import pandas as pd
from tabulate import tabulate
from colorama import Fore, init


def initialize_db():
    """Inizializza il database se non esiste."""
    try:
        # Verifica se la tabella è già creata
        get_all_matches()
    except:
        # Se no, crea una tabella con un record di test
        save_match("Test Match", "Bookmaker Test", 1.80, 3.25, 4.50)
        print("Database inizializzato.")


def main():
    """Funzione principale che gestisce tutto il processo."""
    # Inizializza il database
    initialize_db()
    
    # Ricava i dati simulati dallo scraper
    url = 'https://www.oddsportal.com/football/england/premier-league/'
    teams, odds, dates = scrape_data(url)
    
    # Salva i dati nel database
    for match in zip(teams, *odds):
        save_match(match[0], "Bookmaker Simulato", match[1], match[2], match[3])
    
    # Recupera tutti i record dal database
    df = get_all_matches()
    
    # Analizza le opportunità di VALUE BET
    opportunities = analyze_opportunities(df)
    
    # Stampa il report finale con colorama e tabulate
    init()  # Inizializza colorama
    print(Fore.GREEN + "\n=== RAPPORTO ANALISI ===")
    print(tabulate(opportunities, headers='keys', tablefmt='fancy_grid'))
    print(Fore.RESET)  # Resetta i colori


if __name__ == "__main__":
    main()