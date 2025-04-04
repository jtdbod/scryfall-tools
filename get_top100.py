import requests
from bs4 import BeautifulSoup

def get_top_cards():
    url = "https://edhrec.com/top"  # EDHREC's top cards page
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.select("span.Card_name__Mpa7S")  # Adjust selector based on site structure
    top_cards = [card.text.strip() for card in cards[:100]]  # Get the first 100 cards

    return top_cards

if __name__ == "__main__":
    try:
        top_100_cards = get_top_cards()
        print("Top 100 EDHREC Cards:")
        for i, card in enumerate(top_100_cards, start=1):
            print(f"{i}. {card}")
    except Exception as e:
        print(f"An error occurred: {e}")
