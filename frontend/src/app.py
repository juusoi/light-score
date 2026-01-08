import logging
import os
from typing import Any, Optional, Type, TypeVar, cast

import requests
from flask import Flask, render_template, request

app = Flask(__name__, static_url_path="/static", static_folder="static")

# Configure backend base URL via env var for staging/prod
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

DEFAULT_CONTEXT = {"year": 2025, "week": 1, "seasonType": 2}
T = TypeVar("T")


def _parse_response_json(
    response: requests.Response,
    *,
    expected_type: Type[T],
    default: T,
    label: str,
) -> T:
    """Parse a backend response defensively.

    Ensures we never bubble raw backend error strings into the template. Returns `default`
    when the payload is missing, malformed, or contains a detail/error field.
    """
    try:
        data = response.json()
    except ValueError:
        logging.warning("%s returned non-JSON payload", label)
        return default

    if isinstance(data, dict) and "detail" in data:
        logging.warning("%s responded with detail: %s", label, data["detail"])
        return default

    if isinstance(data, expected_type):
        return data

    logging.warning("%s responded with unexpected type %s", label, type(data).__name__)
    return default


def season_type_name(season_type: Optional[int]) -> str:
    """Convert season type number to readable name.

    Accepts None for robustness (tests call with None)."""
    if season_type is None:
        return "Unknown"
    season_types = {1: "Preseason", 2: "Regular Season", 3: "Postseason"}
    return season_types.get(int(season_type), "Unknown")


def _fetch_playoff_bracket() -> Optional[dict[str, Any]]:
    """Fetch playoff bracket data from backend."""
    try:
        response = requests.get(f"{BACKEND_URL}/playoffs/bracket", timeout=10)
        if response.ok:
            data = response.json()
            if isinstance(data, dict) and "games" in data:
                return data
    except requests.RequestException:
        logging.warning("Failed to fetch playoff bracket")
    return None


def render_bracket_line(
    team1: str,
    score1: Optional[int],
    team2: str,
    score2: Optional[int],
    winner: Optional[str],
) -> str:
    """Render a bracket matchup as text."""
    t1_marker = "►" if winner == team1 else " "
    t2_marker = "►" if winner == team2 else " "
    s1 = str(score1) if score1 is not None else "-"
    s2 = str(score2) if score2 is not None else "-"
    return f"{t1_marker}{team1[:16]:<16} {s1:>2}\n{t2_marker}{team2[:16]:<16} {s2:>2}"


@app.route("/")
def home():
    try:
        # Read raw query params (may be invalid strings)
        raw_year = request.args.get("year")
        raw_week = request.args.get("week")
        raw_season = request.args.get("seasonType")

        def parse_int(value: Optional[str]) -> Optional[int]:
            if value is None or value == "":
                return None
            try:
                return int(value)
            except Exception:
                return None

        # Sanitize values: only forward valid ints within accepted ranges
        year_val = parse_int(raw_year)
        if year_val is not None and not (1970 <= year_val <= 2030):
            year_val = None
        week_val = parse_int(raw_week)
        if week_val is not None and not (1 <= week_val <= 25):
            week_val = None
        season_val = parse_int(raw_season)
        if season_val is not None and season_val not in {1, 2, 3}:
            season_val = None

        sanitized_params = {}
        if year_val is not None:
            sanitized_params["year"] = year_val
        if week_val is not None:
            sanitized_params["week"] = week_val
        if season_val is not None:
            sanitized_params["seasonType"] = season_val

        # Attempt initial fetch with sanitized params
        weekly_response = requests.get(
            f"{BACKEND_URL}/games/weekly", params=sanitized_params, timeout=10
        )
        ctx_resp = requests.get(
            f"{BACKEND_URL}/games/weekly/context", params=sanitized_params, timeout=10
        )

        # If either failed (e.g., upstream ESPN issues / validation), retry with no params for defaults
        if not weekly_response.ok:
            logging.warning(
                "Weekly games request failed (%s) – retrying without params",
                weekly_response.status_code,
            )
            weekly_response = requests.get(
                f"{BACKEND_URL}/games/weekly", params={}, timeout=10
            )
        if not ctx_resp.ok:
            logging.warning(
                "Context request failed (%s) – retrying without params",
                ctx_resp.status_code,
            )
            ctx_resp = requests.get(
                f"{BACKEND_URL}/games/weekly/context", params={}, timeout=10
            )

        # Standings (graceful fallbacks)
        standings_response = requests.get(f"{BACKEND_URL}/standings/live", timeout=10)
        if not standings_response.ok:
            logging.info(
                "Live standings failed (%s) – falling back to cache",
                standings_response.status_code,
            )
            standings_response = requests.get(f"{BACKEND_URL}/standings", timeout=10)
    except requests.RequestException:
        # Network level failure -> show offline template (retain original behavior)
        logging.exception("Network error while fetching data from backend")
        return render_template("home_no_api.html")

    games_payload = cast(
        list[dict[str, Any]],
        (
            _parse_response_json(
                weekly_response,
                expected_type=list,
                default=[],
                label="games/weekly",
            )
            if weekly_response is not None
            else []
        ),
    )

    # Filter out any non-dict entries defensively
    games = [
        g
        for g in games_payload
        if isinstance(g, dict) and {"team_a", "team_b", "status"}.issubset(g.keys())
    ]
    history = [g for g in games if g.get("status") == "final"]
    live = [g for g in games if g.get("status") == "live"]
    upcoming = [g for g in games if g.get("status") == "upcoming"]

    standings_payload = cast(
        list[dict[str, Any]],
        (
            _parse_response_json(
                standings_response,
                expected_type=list,
                default=[],
                label="standings",
            )
            if standings_response is not None
            else []
        ),
    )
    standings_data = [
        row
        for row in standings_payload
        if isinstance(row, dict) and {"team", "wins", "losses"}.issubset(row.keys())
    ]

    ctx_payload = cast(
        dict[str, Any],
        (
            _parse_response_json(
                ctx_resp,
                expected_type=dict,
                default=DEFAULT_CONTEXT,
                label="weekly/context",
            )
            if ctx_resp is not None
            else DEFAULT_CONTEXT
        ),
    )
    ctx = (
        ctx_payload
        if isinstance(ctx_payload, dict)
        and {"year", "week", "seasonType"}.issubset(ctx_payload.keys())
        else DEFAULT_CONTEXT
    )

    # Compute navigation targets from context (always derive defaults)
    def to_int(v, default: int) -> int:
        if v is None:
            return default
        try:
            return int(v)
        except Exception:
            return default

    cur_year = to_int(ctx.get("year"), DEFAULT_CONTEXT["year"])
    cur_week = to_int(ctx.get("week"), DEFAULT_CONTEXT["week"])
    # Respect user's explicit seasonType request (ESPN might return different value)
    cur_type = (
        season_val
        if season_val is not None
        else to_int(ctx.get("seasonType"), DEFAULT_CONTEXT["seasonType"])
    )

    try:
        prev_response = requests.get(
            f"{BACKEND_URL}/games/weekly/navigation",
            params={
                "year": cur_year,
                "week": cur_week,
                "seasonType": cur_type,
                "direction": "prev",
            },
            timeout=5,
        )
        next_response = requests.get(
            f"{BACKEND_URL}/games/weekly/navigation",
            params={
                "year": cur_year,
                "week": cur_week,
                "seasonType": cur_type,
                "direction": "next",
            },
            timeout=5,
        )
        if prev_response.ok and next_response.ok:
            prev_week_params = prev_response.json()
            next_week_params = next_response.json()
        else:
            prev_week_params = {
                "year": cur_year,
                "seasonType": cur_type,
                "week": max(1, cur_week - 1),
            }
            next_week_params = {
                "year": cur_year,
                "seasonType": cur_type,
                "week": cur_week + 1,
            }
    except requests.RequestException:
        prev_week_params = {
            "year": cur_year,
            "seasonType": cur_type,
            "week": max(1, cur_week - 1),
        }
        next_week_params = {
            "year": cur_year,
            "seasonType": cur_type,
            "week": cur_week + 1,
        }

    # Group standings by division (may be empty)
    divisions = {}
    for row in standings_data:
        div = row.get("division") or "Other"
        divisions.setdefault(div, []).append(row)
    for k in divisions:
        try:
            divisions[k].sort(
                key=lambda x: (
                    -int(x.get("wins", 0)),
                    int(x.get("losses", 0)),
                    x.get("team", ""),
                )
            )
        except Exception:  # nosec B110 - Silently fall back to original order on sort failures
            # If parsing fails, keep original order
            pass

    # Fetch playoff bracket during postseason
    bracket_data = None
    if cur_type == 3:  # Postseason
        bracket_data = _fetch_playoff_bracket()

    return render_template(
        "home.html",
        history_games=history,
        live_games=live,
        upcoming_games=upcoming,
        standings=standings_data,
        ctx={"year": cur_year, "week": cur_week, "seasonType": cur_type},
        prev_week_params=prev_week_params,
        next_week_params=next_week_params,
        divisions=divisions,
        season_type_name=season_type_name(cur_type),
        bracket=bracket_data,
    )


@app.route("/playoffs")
def playoffs():
    """Playoff picture page showing team statuses and race standings.

    Supports regular season (seasonType=2) and postseason (seasonType=3).
    """
    try:
        # Read season type from query param, default to 2
        raw_season = request.args.get("seasonType")
        season_type = 2
        if raw_season is not None:
            try:
                val = int(raw_season)
                if val in {2, 3}:
                    season_type = val
            except ValueError:
                pass

        # Fetch playoff picture from backend
        picture_response = requests.get(
            f"{BACKEND_URL}/playoffs/picture",
            params={"seasonType": season_type},
            timeout=10,
        )

        if not picture_response.ok:
            logging.warning(
                "Playoff picture request failed (%s)", picture_response.status_code
            )
            return render_template(
                "playoffs.html", picture=None, error="Data unavailable"
            )

        picture_data = picture_response.json()
        if not isinstance(picture_data, dict):
            return render_template("playoffs.html", picture=None, error="Invalid data")

        return render_template(
            "playoffs.html",
            picture=picture_data,
            season_type_name=season_type_name(season_type),
            error=None,
        )
    except requests.RequestException:
        logging.exception("Network error while fetching playoff picture")
        return render_template("playoffs.html", picture=None, error="Network error")


def main():
    debug = os.getenv("FLASK_DEBUG", "0") in {"1", "true", "True"}
    app.run(debug=debug)


if __name__ == "__main__":
    main()
