import mysql.connector

def create_database():
    """Crea la database 'betting_analytics'."""
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='password'
    )
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS betting_analytics;")
    print("Database creato con successo.")
    cursor.close()
    conn.close()

def insert_match_data(match_id, home_team, away_team, date):
    """Inserisce i dettagli del match nella tabella matches."""
    conn = mysql.connector.connect(
        database='betting_analytics',
        user='root', 
        password='password'
    )
    cursor = conn.cursor()
    query = """
    INSERT INTO matches (match_id, home_team, away_team, date)
    VALUES (%s, %s, %s, %s);
    """
    cursor.execute(query, (match_id, home_team, away_team, date))
    conn.commit()
    print(f"Match {match_id} inserito nella tabella matches.")
    cursor.close()
    conn.close()

def insert_odds_data(match_id, bookmaker, odd_home, odd_away):
    """Inserisce le odds nella tabella odds."""
    conn = mysql.connector.connect(
        database='betting_analytics',
        user='root', 
        password='password'
    )
    cursor = conn.cursor()
    query = """
    INSERT INTO odds (match_id, bookmaker, odd_home, odd_away)
    VALUES (%s, %s, %s, %s);
    """
    cursor.execute(query, (match_id, bookmaker, odd_home, odd_away))
    conn.commit()
    print(f"Odds per {bookmaker} inserite nella tabella odds.")
    cursor.close()
    conn.close()

def get_all_matches():
    """Ritorna tutte le partite con le loro odds."""
    conn = mysql.connector.connect(
        database='betting_analytics',
        user='root', 
        password='password'
    )
    cursor = conn.cursor()
    query = """
    SELECT m.match_id, m.home_team, m.away_team, o.bookmaker, o.odd_home, o.odd_away
    FROM matches as m
    JOIN odds as o ON m.match_id = o.match_id;
    """
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

# Esempio di utilizzo:
if __name__ == "__main__":
    create_database()
    insert_match_data(1, "Inter", "Milan", "2026-01-05")
    insert_odds_data(1, "Bet365", 2.45, 2.75)
    print(get_all_matches())