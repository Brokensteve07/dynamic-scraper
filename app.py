# app.py
from flask import Flask, render_template, redirect, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from scraper import Base, ScrapedItem # Import Base and ScrapedItem from scraper.py
import pytz # for timezone conversion

app = Flask(__name__)

# Re-create engine and session for app.py
db_path = 'database.db'
engine = create_engine(f'sqlite:///{db_path}')
Session = sessionmaker(bind=engine)

@app.route('/')
def index():
    session = Session()
    # Order by market_cap descending to mimic CMC's default 'Top' list
    data = session.query(ScrapedItem).order_by(ScrapedItem.market_cap.desc()).all()
    session.close()
    
    # You might want to format the datetime objects for display if needed
    # (Not strictly necessary as strftime in HTML handles it)
    return render_template("index.html", data=data)

@app.route('/update')
def update():
    # This route will trigger the scraper (assuming update_database() is imported/called)
    # For Render, this is mainly for manual triggers. The Cron Job handles automation.
    from scraper import update_database # Import here to avoid circular dependencies if scraper imports app
    update_database()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)