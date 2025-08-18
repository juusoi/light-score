import requests
from flask import Flask, render_template

app = Flask(__name__, static_url_path="/static", static_folder="static")

BACKEND_URL = "http://localhost:8000"


@app.route("/")
def home():
    try:
        weekly_response = requests.get(f"{BACKEND_URL}/games/weekly")
        # Prefer live standings; fall back to cached /standings on failure
        standings_response = requests.get(f"{BACKEND_URL}/standings/live")
        if not standings_response.ok:
            standings_response = requests.get(f"{BACKEND_URL}/standings")
    # Broad except to keep UX friendly if backend is down/unreachable
    except Exception:
        return render_template("home_no_api.html")

    if weekly_response.ok and standings_response.ok:
        games = weekly_response.json() or []
        history = [g for g in games if g.get("status") == "final"]
        live = [g for g in games if g.get("status") == "live"]
        upcoming = [g for g in games if g.get("status") == "upcoming"]
        standings_data = standings_response.json()
        return render_template(
            "home.html",
            history_games=history,
            live_games=live,
            upcoming_games=upcoming,
            standings=standings_data,
        )
    else:
        return "Error: Could not retrieve data from backend.", 500


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()
