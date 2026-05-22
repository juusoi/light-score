import logging
import os
from typing import Any, Type, TypeVar, cast

import requests
from flask import Flask, render_template, request

app = Flask(__name__, static_url_path="/static", static_folder="static")

# Configure backend base URL via env var for staging/prod
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

DEFAULT_CONTEXT = {"year": 2026, "week": 1, "seasonType": 2}
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


def season_type_name(season_type: int | None) -> str:
    """Convert season type number to readable name.

    Accepts None for robustness (tests call with None)."""
    if season_type is None:
        return "Unknown"
    season_types = {1: "Preseason", 2: "Regular Season", 3: "Postseason"}
    return season_types.get(int(season_type), "Unknown")


def _fetch_playoff_bracket() -> dict[str, Any] | None:
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


# Retro Teletext Team Logos Database
TEAM_LOGOS = {
    "cowboys": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#002244" rx="2"/><polygon points="8,2 10,6 15,6 11,9 13,14 8,11 3,14 5,9 1,6 6,6" fill="#ffffff"/></svg>',
    "packers": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#183028" rx="2"/><circle cx="8" cy="8" r="6" fill="#ffb612"/><circle cx="8" cy="8" r="4.5" fill="#183028"/><rect x="8" y="7.5" width="4" height="2" fill="#ffb612"/><rect x="7" y="6" width="2.5" height="4" fill="#183028"/><rect x="8.5" y="6" width="2" height="2" fill="#ffb612"/></svg>',
    "steelers": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#101820" rx="2"/><path d="M8,1 Q8,4 11,4 Q8,4 8,7 Q8,4 5,4 Q8,4 8,1" fill="#ffb612"/><path d="M12,7 Q12,10 15,10 Q12,10 12,13 Q12,10 9,10 Q12,10 12,7" fill="#c60c30"/><path d="M4,7 Q4,10 7,10 Q4,10 4,13 Q4,10 1,10 Q4,10 4,7" fill="#00539b"/></svg>',
    "chiefs": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#e31837" rx="2"/><polygon points="8,1 15,6 11,14 5,14 1,6" fill="#ffffff"/><text x="8" y="11" font-size="7" font-family="monospace" font-weight="bold" text-anchor="middle" fill="#e31837">KC</text></svg>',
    "raiders": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#101820" rx="2"/><polygon points="2,2 14,2 12,11 8,15 4,11" fill="#a5acaf"/><polygon points="3.5,3 12.5,3 10.5,10.5 8,13.5 5.5,10.5" fill="#101820"/><rect x="5" y="5" width="2" height="2" fill="#a5acaf"/><rect x="9" y="5" width="2" height="2" fill="#a5acaf"/><rect x="6" y="8" width="4" height="2.5" fill="#a5acaf"/></svg>',
    "bills": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#00338d" rx="2"/><path d="M2,8 C4,5 12,5 14,8 C11,11 5,11 2,8" fill="#ffffff"/><rect x="2" y="7" width="12" height="2" fill="#c60c30" transform="rotate(15 8 8)"/></svg>',
    "ravens": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#241773" rx="2"/><path d="M2,6 C4,4 12,4 14,7 C11,11 6,10 2,6" fill="#101820"/><circle cx="10" cy="6.5" r="1" fill="#ffb612"/><polygon points="2,6 6,7 2,8" fill="#ffb612"/></svg>',
    "texans": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#03202f" rx="2"/><rect x="1" y="2" width="7" height="12" fill="#ffffff" rx="1"/><rect x="8" y="2" width="7" height="12" fill="#a71930" rx="1"/><polygon points="3,5 8,8 13,5 8,11" fill="#03202f"/><circle cx="8" cy="8" r="1.5" fill="#ffffff"/></svg>',
    "broncos": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#0c2340" rx="2"/><path d="M2,12 C4,10 6,4 13,5 C10,6 11,9 14,9 C10,10 8,12 2,12" fill="#fc4c02"/><path d="M3,11 C5,10 7,6 12,7 C10,8 10,10 13,10 C10,11 8,11 3,11" fill="#ffffff"/><circle cx="10" cy="8" r="0.8" fill="#fc4c02"/></svg>',
    "chargers": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#0080c6" rx="2"/><polygon points="12,2 5,9 8,9 3,14 11,6 8,6" fill="#ffc20e" stroke="#ffffff" stroke-width="0.75"/></svg>',
    "patriots": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#002244" rx="2"/><path d="M2,5 Q8,2 14,6 Q10,10 2,5" fill="#a5acaf"/><path d="M2,5 Q8,2 14,6 Q10,8 2,9" fill="#c60c30"/><circle cx="5" cy="5" r="1" fill="#ffffff"/></svg>',
    "bengals": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#fb4f14" rx="2"/><line x1="0" y1="3" x2="6" y2="5" stroke="#101820" stroke-width="1.5"/><line x1="16" y1="6" x2="10" y2="8" stroke="#101820" stroke-width="1.5"/><line x1="0" y1="9" x2="8" y2="10" stroke="#101820" stroke-width="1.5"/><line x1="16" y1="12" x2="8" y2="13" stroke="#101820" stroke-width="1.5"/></svg>',
    "browns": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#eb3300" rx="2"/><rect x="6" width="4" height="16" fill="#ffffff"/><rect x="7" width="2" height="16" fill="#311d00"/></svg>',
    "jaguars": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#006778" rx="2"/><circle cx="8" cy="8" r="5" fill="#d7a22a"/><rect x="7" y="5" width="2" height="2" fill="#000000"/><rect x="5" y="8" width="2" height="2" fill="#000000"/><rect x="9" y="8" width="2" height="2" fill="#000000"/><rect x="7" y="10" width="2" height="2" fill="#000000"/></svg>',
    "colts": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#002c5f" rx="2"/><path d="M4,4 L4,9 C4,12 12,12 12,9 L12,4" fill="none" stroke="#ffffff" stroke-width="2.5"/><circle cx="5.5" cy="5" r="0.75" fill="#002c5f"/><circle cx="10.5" cy="5" r="0.75" fill="#002c5f"/><circle cx="5.5" cy="8" r="0.75" fill="#002c5f"/><circle cx="10.5" cy="8" r="0.75" fill="#002c5f"/><circle cx="8" cy="10.5" r="0.75" fill="#002c5f"/></svg>',
    "titans": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#4b92db" rx="2"/><circle cx="8" cy="8" r="5" fill="#c60c30"/><polygon points="8,1 12,6 8,11 4,6" fill="#002244"/><rect x="7" y="4" width="2" height="6" fill="#ffffff"/><rect x="5" y="4" width="6" height="2" fill="#ffffff"/></svg>',
    "jets": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#125740" rx="2"/><ellipse cx="8" cy="8" rx="7" ry="5" fill="none" stroke="#ffffff" stroke-width="1.5"/><text x="8" y="10.5" font-size="6.5" font-family="monospace" font-weight="bold" text-anchor="middle" fill="#ffffff">JETS</text></svg>',
    "giants": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#0b2265" rx="2"/><text x="8" y="11" font-size="8.5" font-family="monospace" font-weight="bold" text-anchor="middle" fill="#ffffff">ny</text></svg>',
    "eagles": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#004c54" rx="2"/><path d="M2,8 C4,4 12,4 14,5 C10,7 12,10 14,10 C10,11 6,12 2,8" fill="#a5acaf"/><path d="M3,8 C5,5 11,5 13,6 C9,8 11,10 13,10 C9,11 6,11 3,8" fill="#ffffff"/></svg>',
    "lions": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#0076b6" rx="2"/><path d="M3,11 C5,8 6,4 13,5 C11,7 13,9 14,11 C10,12 6,12 3,11" fill="#b0b7bc"/><circle cx="5" cy="11" r="1.5" fill="#0076b6"/></svg>',
    "vikings": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#4f2683" rx="2"/><path d="M3,5 C5,5 13,3 12,8 C11,11 6,13 4,9" fill="#ffffff"/><path d="M12,3 C10,5 11,8 12,8 C13,8 14,5 12,3" fill="#ffb612"/></svg>',
    "bears": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#0b2265" rx="2"/><circle cx="8" cy="8" r="6" fill="#c83803"/><circle cx="8" cy="8" r="4" fill="#0b2265"/><rect x="7" y="5" width="6" height="6" fill="#0b2265"/><rect x="8.5" y="4" width="2.5" height="2" fill="#c83803"/><rect x="8.5" y="10" width="2.5" height="2" fill="#c83803"/></svg>',
    "commanders": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#5a1414" rx="2"/><text x="8" y="12" font-size="12" font-family="monospace" font-weight="bold" text-anchor="middle" fill="#ffc20e">W</text></svg>',
    "buccaneers": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#3a3a3a" rx="2"/><rect x="2" y="2" width="12" height="10" fill="#d50a0a"/><circle cx="8" cy="6" r="2" fill="#ffffff"/><line x1="5" y1="9" x2="11" y2="9" stroke="#ffffff" stroke-width="1.5"/></svg>',
    "falcons": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#000000" rx="2"/><polygon points="2,4 14,4 12,8 8,12 4,8" fill="#a71930"/><polygon points="4,4 12,4 10,7 8,9 6,7" fill="#ffffff"/></svg>',
    "panthers": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#101820" rx="2"/><path d="M2,6 C4,4 12,4 14,7 C10,9 12,12 14,12 C10,13 6,11 2,6" fill="#0085ca"/><circle cx="10" cy="7" r="1" fill="#ffffff"/></svg>',
    "saints": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#101820" rx="2"/><path d="M8,2 C8,5 11,8 11,10 C11,12 9,13 8,13 C7,13 5,12 5,10 C5,8 8,5 8,2" fill="#d3bc8d"/><line x1="4" y1="10" x2="12" y2="10" stroke="#d3bc8d" stroke-width="2"/></svg>',
    "49ers": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#aa0000" rx="2"/><ellipse cx="8" cy="8" rx="7" ry="5" fill="#b3995d" stroke="#ffffff" stroke-width="0.75"/><text x="8" y="11" font-size="7.5" font-family="monospace" font-weight="bold" text-anchor="middle" fill="#ffffff">SF</text></svg>',
    "rams": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#003594" rx="2"/><path d="M3,5 C7,1 13,3 13,8 C13,11 10,13 8,11 C9,9 11,8 10,5" fill="none" stroke="#ffa300" stroke-width="2.5"/></svg>',
    "seahawks": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#002244" rx="2"/><path d="M2,7 C4,5 12,5 14,8 C11,10 6,10 2,7" fill="#69be28"/><circle cx="10" cy="7" r="1.2" fill="#ffffff"/><circle cx="10.5" cy="7" r="0.6" fill="#002244"/></svg>',
    "cardinals": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#97233f" rx="2"/><path d="M2,6 C4,4 10,4 12,6 C10,9 12,12 12,12 C10,12 6,11 2,6" fill="#ffffff"/><polygon points="9,7 13,8 9,10" fill="#ffb612"/></svg>',
    "dolphins": '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><rect width="16" height="16" fill="#008e97" rx="2"/><circle cx="8" cy="8" r="5" fill="#fc4c02"/><path d="M3,10 C5,7 10,5 14,8 C11,9 8,11 3,10" fill="#ffffff"/><circle cx="11" cy="7" r="0.8" fill="#fc4c02"/></svg>',
}


def get_team_logo(team_name: str | None) -> str:
    """Resolve high-fidelity teletext styled inline SVG team logo.

    Matches case-insensitively using simple substring matching to ensure
    complete resilience across full names and abbreviations.
    """
    if not team_name:
        return ""
    name_lower = team_name.lower()
    for key, svg in TEAM_LOGOS.items():
        if key in name_lower:
            return svg
    # Robust fallback: striped green and blue retro block
    return (
        '<svg class="ttx-logo" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">'
        '<rect width="8" height="16" fill="#00ff00"/>'
        '<rect x="8" width="8" height="16" fill="#00aaff"/>'
        "</svg>"
    )


@app.template_filter("team_logo")
def team_logo_filter(team_name):
    return get_team_logo(team_name)


@app.context_processor
def inject_team_logo():
    return dict(team_logo=get_team_logo)


@app.route("/")
def home():
    try:
        # Read raw query params (may be invalid strings)
        raw_year = request.args.get("year")
        raw_week = request.args.get("week")
        raw_season = request.args.get("seasonType")

        def parse_int(value: str | None) -> int | None:
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

        # If either failed (e.g., upstream ESPN issues / validation):
        # - If specific parameters were explicitly requested, raise HTTPError immediately to trigger the offline/error template
        #   instead of silently displaying mismatched/fallback active week data.
        # - Otherwise, retry with empty parameters (though sanitized_params is already empty, this preserves fallback).
        if not weekly_response.ok or not ctx_resp.ok:
            if sanitized_params:
                if not weekly_response.ok:
                    weekly_response.raise_for_status()
                if not ctx_resp.ok:
                    ctx_resp.raise_for_status()
            else:
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

        # Get context year to pass to standings
        standings_year = year_val
        if standings_year is None:
            if ctx_resp is not None and ctx_resp.ok:
                try:
                    standings_year = ctx_resp.json().get("year")
                except Exception:  # nosec B110
                    pass
        if standings_year is None:
            standings_year = DEFAULT_CONTEXT["year"]

        # Standings (graceful fallbacks)
        standings_response = requests.get(
            f"{BACKEND_URL}/standings/live",
            params={"year": standings_year},
            timeout=10,
        )
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


def main():
    debug = os.getenv("FLASK_DEBUG", "0") in {"1", "true", "True"}
    app.run(debug=debug)


if __name__ == "__main__":
    main()
