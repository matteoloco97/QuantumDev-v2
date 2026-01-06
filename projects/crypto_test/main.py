import requests
response = requests.get('https://api.coindesk.com/v1/bpi/currentprice.json')
data = response.json()
price = data['bpi']['USD']['rate']
print(f"The current Bitcoin price is ${price}.")