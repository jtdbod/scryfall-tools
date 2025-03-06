import requests

import requests

base_url = "https://api.scryfall.com/"
search_query = "counterspell"
search_url = f"{base_url}cards/search?q={search_query}"

while search_url:
    response = requests.get(search_url)
    if response.status_code == 200:
        data = response.json()
        
        # Print the names of the cards found in this page
        for card in data['data']:
            print(card['name'])
        
        # Get the next page if available
        search_url = data.get('next_page', None)
        time.sleep(0.1)
    else:
        print(f"Error: {response.status_code}")
        break

