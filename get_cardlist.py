import requests
import time
import certifi
import pandas as pd
import numpy as np

class CardList:
    def __init__(self):
        self.data = pd.DataFrame({'name': [], 'price': [], 'fullart': [], 'frame': [], 'frame_effects': [], 'border_color': [], 'collector_number': []})

    def add_card(self, card):
        self.data = pd.concat([self.data, pd.DataFrame([card])], ignore_index=True)

    def get_data(self):
        return self.data

class Buylist:
    def __init__(self):
        self.data = pd.DataFrame()
        self.no_prices = None

    def add_entry(self, name, price, collector_number):
        self.data = pd.concat([self.data, pd.DataFrame([{'Quantity': 1, 'Name': name, 'CN': collector_number, 'Price': float(price)}])], ignore_index=True)

    def adjust_quantity(self, index, adjust: int = 1):
        self.data.at[index, 'Quantity'] += adjust
        if self.data.at[index, 'Quantity'] < 1:
            self.data.drop(index, inplace = True)

    def sort_buylist(self):
        self.data = self.data.sort_values(by="Name")

    def export_to_excel(self, filename='buylist.xlsx'):
        self.data.to_excel(filename, index=False)

    def get_data(self):
        return self.data
    
    def get_totals(self):
        total_cards = self.data['Quantity'].sum()
        total_price = (self.data['Price']*self.data['Quantity']).sum()
        print(f"Total Cards: {total_cards} | Total Price: ${total_price:.2f}")
        print(f"Cards without Prices: {self.no_prices}")
        return self.data['Quantity'].sum(), self.data['Price'].sum()

class ScryfallCardFetcher:
    BASE_URL = "https://api.scryfall.com/"
    HEADERS = {"User-Agent": "scyrfall_tools/1.0 (jackson.travis.do@gmail.com)"}
    VALID_SPECIALS = {'showcase', 'retro', 'borderless', 'extendedart'}

    def __init__(self, set_code: str, max_price: float = None, copies: int = 4, max_retries: int = 3, exclude_reprints: bool = True, exclude_special: list = None):
        self.set_code = set_code
        self.max_price = max_price
        self.copies = copies
        self.max_retries = max_retries
        self.exclude_special = [s for s in (exclude_special or []) if s in self.VALID_SPECIALS]
        self.exclude_reprints = exclude_reprints
        self.card_list = CardList()
        self.buylist = Buylist()

    def build_query(self) -> str:
        query = f"s:{self.set_code} unique:prints -type:basic r>u"
        if self.exclude_reprints:
            query = query + ' -is:reprint'
        if self.max_price is not None:
            query = query + f' usd<{self.max_price}'

        return query

    def fetch_cards(self, query):
        search_url = f"{self.BASE_URL}cards/search?q={query}"
        while search_url:
            for attempt in range(self.max_retries):
                try:
                    response = requests.get(search_url, headers=self.HEADERS, verify=False)
                    response.raise_for_status()
                    data = response.json()
                    self.process_cards(data['data'])
                    search_url = data.get('next_page', None)
                    time.sleep(0.1)
                    break
                except requests.exceptions.RequestException as e:
                    print(f"Attempt {attempt + 1} failed: {e}")
                    if attempt == self.max_retries - 1:
                        print("Max retries reached. Skipping this request.")
                        search_url = None

    def process_cards(self, cards: list):
        for card in cards:
            frame_effects = card.get('frame_effects', [])
            frame_effects = frame_effects if isinstance(frame_effects, list) else [frame_effects]
            retro_effects = card.get('frame', [])
            retro_effects = retro_effects if isinstance(retro_effects, list) else [retro_effects]
            border_effects = card.get('border_color', [])
            border_effects = border_effects if isinstance(border_effects, list) else [border_effects]

            alternate_arts = frame_effects + retro_effects + border_effects

            if any(effect.replace('1997', 'retro') in self.exclude_special for effect in alternate_arts):
                continue

            entry = {
                'name': card['name'],
                'price': card['prices']['usd'],
                'fullart': card.get('full_art', False),
                'frame': card.get('frame', ''),
                'border_color': card.get('border_color', ''),
                'frame_effects': frame_effects,
                'collector_number': card['collector_number']
            }
            if entry['price'] is None:
                entry['price'] = np.inf

            self.card_list.add_card(entry)

    def get_tcgplayer_name(self, card):
        entry = card['name']
        entry = entry.split(' //')[0]
        if 'showcase' in card.get('frame_effects', []):
            entry = f"{entry} (Showcase)"
        if 'extendedart' in card.get('frame_effects', []):
            entry = f"{entry} (Extended Art)"
        if '1997' in card.get('frame'):
            entry = f"{entry} (Retro Frame)"
        if 'borderless' in card.get('border_color'):
            entry = f"{entry} (Borderless)"
        return entry

    def generate_buylist(self):
        for name in self.card_list.get_data()['name'].unique():
            cards = self.card_list.get_data()[self.card_list.get_data()['name'] == name]
            for _, card in cards.iterrows():
                #entry = self.get_tcgplayer_name(card)
                self.buylist.add_entry(card['name'], card['price'], card['collector_number'])

            while self.buylist.get_data()[self.buylist.get_data()['Name'].str.contains(name.split(' //')[0])]['Quantity'].sum() > self.copies:
                current_prints = self.buylist.get_data()[self.buylist.get_data()['Name'].str.contains(name.split(' //')[0])]
                to_drop = current_prints['Price'].dropna().idxmax()
                self.buylist.adjust_quantity(to_drop, -1)              

            while self.buylist.get_data()[self.buylist.get_data()['Name'].str.contains(name.split(' //')[0])]['Quantity'].sum() < self.copies:
                to_add = cards['price'].dropna().idxmin()
                self.buylist.adjust_quantity(to_add, 1)

        self.buylist.sort_buylist()
        # Drop cards without price
        no_prices = self.buylist.get_data()[np.isinf(self.buylist.get_data()['Price'])]
        self.buylist.get_data().drop(no_prices.index, inplace=True)
        self.buylist.no_prices = no_prices

# Example usage
if __name__ == "__main__":
    #fetcher = ScryfallCardFetcher(set_code='tdc', max_price=1000, copies = 1, exclude_reprints = True)
    fetcher = ScryfallCardFetcher(set_code='tdm', copies = 2)
    query = fetcher.build_query()
    fetcher.fetch_cards(query)
    fetcher.generate_buylist()
    print(fetcher.buylist.get_data())
    print(fetcher.buylist.get_totals())
    #fetcher.buylist.export_to_excel('buylist.xlsx')
    print(fetcher.buylist.get_data())