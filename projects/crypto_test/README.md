import requests

def get_bitcoin_price():
    response = requests.get('https://api.coindesk.com/v1/bpi/currentprice.json')
    data = response.json()
    price = data['bpi']['USD']['rate']
    print(f"Prezzo del Bitcoin: ${price:,}")

get_bitcoin_price()