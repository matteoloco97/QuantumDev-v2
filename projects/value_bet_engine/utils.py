def save_to_json(data, filename):
    """Salva i dati in un file JSON specificando il path dall'config.json."""
    import json
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)