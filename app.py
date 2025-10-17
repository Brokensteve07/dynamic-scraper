from flask import Flask, render_template, redirect, url_for
from scraper import get_all_data, update_database

app = Flask(__name__)

@app.route("/")
def index():
    data = get_all_data()
    return render_template("index.html", data=data)

@app.route("/update")          # <-- note the endpoint name
def update():                  # <-- this function name is used in url_for()
    update_database()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
