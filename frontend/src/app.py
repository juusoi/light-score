import requests
from flask import Flask, render_template, request

app = Flask(__name__, static_url_path="/static", static_folder="static")

BACKEND_URL = "http://localhost:8000"


@app.route("/")
def home():
    try:
        # Read selection params from query
        year = request.args.get("year")
        week = request.args.get("week")
        seasonType = request.args.get("seasonType")

        params = {}
        if year:
            params["year"] = year
        if week:
            params["week"] = week
        if seasonType:
            params["seasonType"] = seasonType

        weekly_response = requests.get(f"{BACKEND_URL}/games/weekly", params=params)
        # Fetch context (resolves defaults if params missing)
        ctx_resp = requests.get(f"{BACKEND_URL}/games/weekly/context", params=params)
        # Prefer live standings; fall back to cached /standings on failure
        standings_response = requests.get(f"{BACKEND_URL}/standings/live")
        if not standings_response.ok:
            standings_response = requests.get(f"{BACKEND_URL}/standings")
    # Broad except to keep UX friendly if backend is down/unreachable
    except Exception:
        return render_template("home_no_api.html")

    if weekly_response.ok and standings_response.ok and ctx_resp.ok:
        games = weekly_response.json() or []
        history = [g for g in games if g.get("status") == "final"]
        live = [g for g in games if g.get("status") == "live"]
        upcoming = [g for g in games if g.get("status") == "upcoming"]
        standings_data = standings_response.json()
        ctx = ctx_resp.json() or {}
        # Compute navigation targets
        def to_int(v, default):
            try:
                return int(v)
            except Exception:
                return default

        cur_year = to_int(ctx.get("year"), 2025)
        cur_week = to_int(ctx.get("week"), 1)
        cur_type = to_int(ctx.get("seasonType"), 2)

        prev_week_params = {"year": cur_year, "seasonType": cur_type, "week": max(1, cur_week - 1)}
        next_week_params = {"year": cur_year, "seasonType": cur_type, "week": cur_week + 1}
        prev_season_params = {"year": cur_year - 1, "seasonType": cur_type, "week": cur_week}
        next_season_params = {"year": cur_year + 1, "seasonType": cur_type, "week": cur_week}

        return render_template(
            "home.html",
            history_games=history,
            live_games=live,
            upcoming_games=upcoming,
            standings=standings_data,
            ctx=ctx,
            prev_week_params=prev_week_params,
            next_week_params=next_week_params,
            prev_season_params=prev_season_params,
            next_season_params=next_season_params,
        )
    else:
        return "Error: Could not retrieve data from backend.", 500


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()
