# scraper.py

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import requests
import re # For regular expressions, used for data cleaning

# --- 1. Database Setup ---
# Initialize the database connection
DATABASE_URL = "sqlite:///database.db"
Engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=Engine)

# --- 2. Data Model Definition (Matching the Frontend/UI) ---
class ScrapedItem(Base):
    __tablename__ = 'scraped_data'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    icon_url = Column(String)
    value = Column(Float, nullable=False) # Price
    change_1h = Column(Float)
    change_24h = Column(Float)
    change_7d = Column(Float)
    market_cap = Column(Float)
    volume_24h = Column(Float)
    circulating_supply = Column(Float)
    last_updated = Column(DateTime, default=datetime.utcnow)

# Ensure the table is created/updated (IMPORTANT after adding new columns)
Base.metadata.create_all(Engine)


# --- 3. Data Cleaning Utilities ---

def convert_suffix_to_number(value_str):
    """Converts strings like '$1.5B' or '300M' into a float."""
    if not isinstance(value_str, (str, int, float)):
        return None
    if isinstance(value_str, (int, float)):
        return float(value_str)

    value_str = value_str.upper().replace('$', '').replace(',', '').strip()
    
    if 'T' in value_str:
        return float(re.sub(r'[^\d.]', '', value_str)) * 1_000_000_000_000
    if 'B' in value_str:
        return float(re.sub(r'[^\d.]', '', value_str)) * 1_000_000_000
    if 'M' in value_str:
        return float(value_str.strip('M')) * 1_000_000
    if 'K' in value_str:
        return float(value_str.strip('K')) * 1_000
    
    try:
        return float(value_str)
    except ValueError:
        return None


# --- 4. Web Scraping Logic (Using Internal API) ---

def scrape_data():
    """Fetches comprehensive crypto data from CoinMarketCap's public data API."""
    
    # This is a stable internal API endpoint that returns JSON data
    # start=1&limit=100 will fetch the top 100 coins
    API_URL = 'https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing?start=1&limit=100&sortBy=market_cap&sortType=desc&convert=USD&cryptoType=all&tagType=all&aux=ath,atl,high24h,low24h,num_market_pairs,cmc_rank,date_added,max_supply,circulating_supply,total_supply,volume7d,volume30d'
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    crypto_data = []

    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=15)
        response.raise_for_status() 
        json_data = response.json()

        # Drill down to the list of crypto items
        data_list = json_data['data']['cryptoCurrencyList']
        
        for item in data_list:
            quote = item.get('quotes', [{}])[0] # Get the USD quote data
            
            # Construct the icon URL using the CMC ID
            icon_id = item.get('id')
            icon_url = f"https://s2.coinmarketcap.com/static/img/coins/64x64/{icon_id}.png"
            
            crypto_data.append({
                'name': item.get('name'),
                'symbol': item.get('symbol'),
                'icon_url': icon_url,
                'value': quote.get('price'),
                'change_1h': quote.get('percentChange1h'),
                'change_24h': quote.get('percentChange24h'),
                'change_7d': quote.get('percentChange7d'),
                'market_cap': quote.get('marketCap'),
                'volume_24h': quote.get('volume24h'),
                'circulating_supply': item.get('circulatingSupply'),
            })

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return []
    except Exception as e:
        print(f"Error parsing JSON or data structure changed: {e}")
        return []
        
    return crypto_data

# --- 5. Database Update Logic ---

def update_database():
    """Scrapes data and performs an upsert (UPDATE or INSERT) into the database."""
    scraped_items = scrape_data()
    if not scraped_items:
        print("No valid data scraped. Database not updated.")
        return

    session = Session()
    start_time = datetime.now()
    
    try:
        for item_data in scraped_items:
            # Check for name or symbol to find existing record
            record = session.query(ScrapedItem).filter_by(symbol=item_data['symbol']).first()
            
            if record:
                # UPDATE existing record
                record.name = item_data['name']
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
                # INSERT new record
                new_record = ScrapedItem(**item_data, last_updated=datetime.utcnow())
                session.add(new_record)
        
        session.commit()
        print(f"Database update successful. Time taken: {datetime.now() - start_time}")
        
    except Exception as e:
        session.rollback()
        print(f"CRITICAL ERROR during DB transaction: {e}")
    finally:
        session.close()

# --- 6. Data Retrieval Logic (for Flask App) ---

def get_all_data():
    """Fetches all records from the database, ordered by market cap."""
    session = Session()
    try:
        # Order by Market Cap descending to mimic CMC ranking
        data = session.query(ScrapedItem).order_by(ScrapedItem.market_cap.desc()).all() 
        return data
    except Exception as e:
        print(f"Error retrieving data: {e}")
        return []
    finally:
        session.close()

if __name__ == '__main__':
    update_database()