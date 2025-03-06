import requests
import time
import certifi
import pandas as pd

base_url = "https://api.scryfall.com/"
search_query = "t:creature cmc<3 o:flying s:one"
search_url = f"{base_url}cards/search?q={search_query}"
headers = {
        "User-Agent": "scyrfall_tools/1.0 (jackson.travis.do@gmail.com)"  # Replace with your app name and email
    }

df = pd.DataFrame()

while search_url:
    response = requests.get(search_url, headers=headers, verify=False)
    if response.status_code == 200:
        data = response.json()
        
        # Print the names of the cards found in this page
        for card in data['data']:
            print(f"{card['name']} \t\t\t {card['prices']['usd']}")
            
        search_url = data.get('next_page', None)
        time.sleep(0.1)
    else:
        print("Error:", response.status_code, response.json().get("details"))



