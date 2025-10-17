# scraper.py

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import requests

# --- Database Setup ---
DATABASE_URL = "sqlite:///database.db"
Engine = create_engine(DATABASE_URL, echo=False)
Base = declarative_base()
Session = sessionmaker(bind=Engine)

# --- Data Model ---
class ScrapedItem(Base):
    __tablename__ = 'scraped_data'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    value = Column(Float, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ScrapedItem(name='{self.name}', value={self.value}, updated='{self.last_updated}')>"

Base.metadata.create_all(Engine)

# --- Scraper Function using CoinGecko API ---
def scrape_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 5,
        "page": 1
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching API data: {e}")
        return []

    scraped_items = []
    for coin in data:
        name = coin["symbol"].upper()
        value = float(coin["current_price"])
        scraped_items.append({"name": name, "value": value})

    return scraped_items

# --- Update Database ---
def update_database():
    items = scrape_data()
    if not items:
        print("No data scraped. Exiting.")
        return

    session = Session()
    for item in items:
        record = session.query(ScrapedItem).filter_by(name=item['name']).first()
        if record:
            record.value = item['value']
            record.last_updated = datetime.utcnow()
        else:
            session.add(ScrapedItem(name=item['name'], value=item['value']))
    session.commit()
    session.close()
    print("Database updated successfully!")

# --- Get all data ---
def get_all_data():
    session = Session()
    data = session.query(ScrapedItem).order_by(ScrapedItem.name).all()
    session.close()
    return data

# --- Manual Test ---
if __name__ == "__main__":
    update_database()
    print("Current DB records:")
    for item in get_all_data():
        print(item)
