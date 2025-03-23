import requests
import time
import certifi
import pandas as pd

class CardList:
    def __init__(self):
        self.data = pd.DataFrame({'name': [], 'price': [], 'fullart': [], 'frame': [], 'frame_effects': [], 'border_color': []})

    def add_card(self, card):
        self.data = pd.concat([self.data, pd.DataFrame([card])], ignore_index=True)

    def get_data(self):
        return self.data

class Buylist:
    def __init__(self):
        self.data = pd.DataFrame()

    def add_entry(self, name, price):
        self.data = pd.concat([self.data, pd.DataFrame([{'Quantity': 1, 'Name': name, 'Price': float(price)}])], ignore_index=True)

    def adjust_quantity(self, name, adjust: int = 1):
        self.data.loc[self.data['Name'] == name, 'Quantity'] += adjust
        if self.data.loc[self.data['Name'] == name]['Quantity'].values < 1:
            self.data.drop(self.data.loc[self.data['Name'] == name].index, inplace = True)

    def sort_buylist(self):
        self.data = self.data.sort_values(by="Name")

    def export_to_excel(self, filename='buylist.xlsx'):
        self.data.to_excel(filename, index=False)

    def get_data(self):
        return self.data

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

    def fetch_cards(self):
        search_url = f"{self.BASE_URL}cards/search?q={self.build_query()}"
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
                'frame_effects': frame_effects
            }
            if entry['price'] is None:
                entry['price'] = 0

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
                entry = self.get_tcgplayer_name(card)
                self.buylist.add_entry(entry, card['price'])

            while self.buylist.get_data()[self.buylist.get_data()['Name'].str.contains(name.split(' //')[0])]['Quantity'].sum() > self.copies:
                current_prints = self.buylist.get_data()[self.buylist.get_data()['Name'].str.contains(name.split(' //')[0])]
                to_drop = current_prints.loc[current_prints['Price'].dropna().idxmax()]['Name']
                self.buylist.adjust_quantity(to_drop, -1)              

            while self.buylist.get_data()[self.buylist.get_data()['Name'].str.contains(name.split(' //')[0])]['Quantity'].sum() < self.copies:
                to_add = cards.loc[cards['price'].dropna().idxmin()]
                self.buylist.adjust_quantity(self.get_tcgplayer_name(to_add), 1)
                print(self.get_tcgplayer_name(to_add))

        self.buylist.sort_buylist()

# Example usage
if __name__ == "__main__":
    #fetcher = ScryfallCardFetcher(set_code='tdc', max_price=1000, copies = 1, exclude_reprints = True)
    fetcher = ScryfallCardFetcher(set_code='tdc', copies = 1, exclude_reprints = True)
    fetcher.fetch_cards()
    fetcher.generate_buylist()
    print(fetcher.buylist.get_data())
    #fetcher.buylist.export_to_excel('buylist.xlsx')
