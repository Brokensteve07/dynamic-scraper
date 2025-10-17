# scraper.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import os

# Define the database path
db_path = 'database.db'
engine = create_engine(f'sqlite:///{db_path}')
Base = declarative_base()

class ScrapedItem(Base):
    __tablename__ = 'scraped_items'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    symbol = Column(String, nullable=False) # NEW: To store BTC, ETH etc.
    icon_url = Column(String)              # NEW: For cryptocurrency icons
    value = Column(Float, nullable=False)
    change_1h = Column(Float)              # NEW: 1-hour percentage change
    change_24h = Column(Float)             # NEW: 24-hour percentage change
    change_7d = Column(Float)              # NEW: 7-day percentage change
    market_cap = Column(Float)             # NEW: Market Cap
    volume_24h = Column(Float)             # NEW: 24-hour Volume
    circulating_supply = Column(Float)     # NEW: Circulating Supply
    last_updated = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ScrapedItem(name='{self.name}', value='{self.value}')>"

# Create tables (only if they don't exist)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

def scrape_coinmarketcap():
    url = "https://coinmarketcap.com/" # This URL might change or need adjustments for API
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    # !! IMPORTANT !!
    # CoinMarketCap uses dynamic content loaded by JavaScript.
    # Direct scraping of the HTML like this might only get static content or empty tables.
    # You might need to:
    # 1. Use a headless browser (like Selenium) to render the page first.
    # 2. Look for an unofficial API endpoint that CMC uses (often found in browser dev tools -> Network tab).
    # 3. Use an official (but likely paid) CoinMarketCap API.
    # For this example, I'll assume some elements are available via direct scrape,
    # but be prepared for it to be difficult without Selenium/API.

    crypto_data = []
    # This selector is a GUESS and will almost certainly need adjustment
    # based on real-time inspection of CMC's current HTML structure.
    # Inspect the <tbody> within the main table on CMC.
    table_rows = soup.select('table > tbody > tr') # This needs to be more specific
    
    # Try to find a script tag with initial data, sometimes sites embed JSON
    # script_tag = soup.find('script', id='__NEXT_DATA__')
    # if script_tag:
    #     import json
    #     data = json.loads(script_tag.string)
    #     # Parse data['props']['pageProps']['initialProps']['pageData'] or similar structure
    #     # This is usually the most robust way if available.

    for row in table_rows:
        try:
            # These selectors are highly speculative and need to be found by
            # inspecting CoinMarketCap's current HTML structure using browser developer tools.
            # Example:
            # name_element = row.select_one('p.coin-name')
            # price_element = row.select_one('div.price-value')
            # market_cap_element = row.select_one('span.market-cap')

            name = row.select_one('.cmc-table__column-name').text.strip() # This is a guess
            symbol = row.select_one('.cmc-table__column-symbol').text.strip() # Guess
            icon_url = row.select_one('.coin-icon img')['src'] # Guess
            
            price_str = row.select_one('.cmc-table__column-price').text.strip().replace('$', '').replace(',', '') # Guess
            price = float(price_str)

            change_1h_str = row.select_one('.cmc-table__column-change--1h').text.strip().replace('%', '') # Guess
            change_1h = float(change_1h_str)

            change_24h_str = row.select_one('.cmc-table__column-change--24h').text.strip().replace('%', '') # Guess
            change_24h = float(change_24h_str)

            change_7d_str = row.select_one('.cmc-table__column-change--7d').text.strip().replace('%', '') # Guess
            change_7d = float(change_7d_str)

            market_cap_str = row.select_one('.cmc-table__column-market-cap').text.strip().replace('$', '').replace(',', '') # Guess
            market_cap = float(market_cap_str)

            volume_24h_str = row.select_one('.cmc-table__column-volume').text.strip().replace('$', '').replace(',', '') # Guess
            volume_24h = float(volume_24h_str)

            circulating_supply_str = row.select_one('.cmc-table__column-supply').text.strip().replace(',', '') # Guess
            # This might require more complex parsing if it has 'B', 'M', 'K' suffixes
            circulating_supply = float(circulating_supply_str)

            crypto_data.append({
                'name': name,
                'symbol': symbol,
                'icon_url': icon_url,
                'value': price,
                'change_1h': change_1h,
                'change_24h': change_24h,
                'change_7d': change_7d,
                'market_cap': market_cap,
                'volume_24h': volume_24h,
                'circulating_supply': circulating_supply
            })
        except AttributeError:
            # Handle cases where a selector doesn't find an element in a row
            print(f"Skipping row due to missing element: {row}")
            continue
        except ValueError as e:
            # Handle conversion errors if text isn't a valid number
            print(f"Skipping row due to data conversion error: {e} in row: {row}")
            continue
    return crypto_data

def update_database():
    session = Session()
    try:
        data = scrape_coinmarketcap()
        for item_data in data:
            # Try to find an existing record by name
            record = session.query(ScrapedItem).filter_by(name=item_data['name']).first()

            if record:
                # Update existing record
                record.symbol = item_data['symbol']
                record.icon_url = item_data['icon_url']
                record.value = item_data['value']
                record.change_1h = item_data['change_1h']
                record.change_24h = item_data['change_24h']
                record.change_7d = item_data['change_7d']
                record.market_cap = item_data['market_cap']
                record.volume_24h = item_data['volume_24h']
                record.circulating_supply = item_data['circulating_supply']
                record.last_updated = datetime.utcnow()
            else:
                # Insert new record
                new_record = ScrapedItem(
                    name=item_data['name'],
                    symbol=item_data['symbol'],
                    icon_url=item_data['icon_url'],
                    value=item_data['value'],
                    change_1h=item_data['change_1h'],
                    change_24h=item_data['change_24h'],
                    change_7d=item_data['change_7d'],
                    market_cap=item_data['market_cap'],
                    volume_24h=item_data['volume_24h'],
                    circulating_supply=item_data['circulating_supply'],
                    last_updated=datetime.utcnow()
                )
                session.add(new_record)
        session.commit()
        print("Database update complete.")
    except Exception as e:
        session.rollback()
        print(f"Error during database update: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    update_database()