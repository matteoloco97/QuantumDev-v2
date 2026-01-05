# main.py

from database import save_match, get_all_matches
from scraper import scrape_data
from analyzer import analyze_opportunities
import pandas as pd
from tabulate import tabulate
from colorama import Fore, init


def initialize_db():
    """Inizializza il database SQLite."""
    # Verifica che la tabella sia creata
    try:
        get_all_matches()
    except:
        save_match("test", "test", "test", 1.80, 1.85, 1.90)
        print("Database inizializzato.")


def main():
    # Inizializza il database
    initialize_db()

    # Esegui lo scrape dei dati simulati
    teams, odds, dates = scrape_data(
        url='https://www.oddsportal.com/football/england/premier-league/',
        class_team='team',
        class_odds='odds',
        class_date='date'
    )

    # Salva i match nel database
    for team, odd, date in zip(teams, odds, dates):
        save_match(
            match=team,
            bookmaker="Bet365",
            odd_1=odd[0],
            odd_x=odd[1],
            odd_2=odd[2],
            timestamp=date
        )

    # Ottieni tutti i match dal database
    df = get_all_matches()

    # Analizza le opportunità di value bet
    opportunities = analyze_opportunities(df)

    # Stampa il report finale
    print("\n\n")
    print(Fore.GREEN + "=" * 30)
    print("Value Bets disponibili:")
    print("=" * 30)
    print(tabulate(opportunities, headers='keys', tablefmt='pretty'))
    print(Fore.RESET)

if __name__ == "__main__":
    main()