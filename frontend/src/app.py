import requests
from flask import Flask, render_template

app = Flask(__name__)

BACKEND_URL = "http://localhost:8000"


@app.route("/")
def home():
    games_response = requests.get(f"{BACKEND_URL}/games")
    standings_response = requests.get(f"{BACKEND_URL}/standings")

    if games_response.ok and standings_response.ok:
        games_data = games_response.json()
        standings_data = standings_response.json()
        return render_template("home.html", games=games_data, standings=standings_data)
    else:
        return render_template("home_local.html")


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()
