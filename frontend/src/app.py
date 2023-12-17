import requests
from flask import Flask, render_template

app = Flask(__name__)

BACKEND_URL = "http://localhost:8000"


@app.route("/")
def home():
    try:
        games_response = requests.get(f"{BACKEND_URL}/games")
        standings_response = requests.get(f"{BACKEND_URL}/standings")
    except requests.exceptions.ConnectionError:
        return render_template("home_no_api.html")

    if games_response.ok and standings_response.ok:
        games_data = games_response.json()
        standings_data = standings_response.json()
        return render_template("home.html", games=games_data, standings=standings_data)
    else:
        return "Error: Could not retrieve data from backend.", 500


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()
