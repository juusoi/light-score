import json
import time
from datetime import datetime
from pathlib import Path
from typing import List
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# Timezone utilities
FINNISH_TZ = ZoneInfo("Europe/Helsinki")


def format_finnish_time(iso_time_str: str) -> str:
    """Convert UTC ISO time to Finnish local time format."""
    try:
        utc_time = datetime.fromisoformat(iso_time_str.replace("Z", "+00:00"))
        finnish_time = utc_time.astimezone(FINNISH_TZ)
        return finnish_time.strftime("%H:%M")
    except (ValueError, TypeError):
        return iso_time_str


def format_finnish_date_time(iso_time_str: str) -> str:
    """Convert UTC ISO time to Finnish local date and time format."""
    try:
        utc_time = datetime.fromisoformat(iso_time_str.replace("Z", "+00:00"))
        finnish_time = utc_time.astimezone(FINNISH_TZ)
        # Format as "Wed 20.8. 23:15"
        return finnish_time.strftime("%a %d.%m. %H:%M")
    except (ValueError, TypeError):
        return iso_time_str


def extract_game_time(game_data: dict) -> str | None:
    """Extract game clock/period from live game data."""
    try:
        status = game_data.get("status", {})
        if status.get("type", {}).get("name") == "STATUS_IN_PROGRESS":
            display_clock = status.get("displayClock", "")
            period = status.get("period", 0)
            if display_clock and period:
                return f"Q{period} {display_clock}"
            elif period:
                return f"Q{period}"
        return None
    except (KeyError, TypeError, AttributeError):
        return None


app = FastAPI()


class Game(BaseModel):
    team_a: str
    team_b: str
    score_a: int
    score_b: int


class Standings(BaseModel):
    team: str
    wins: int
    losses: int
    division: str | None = None


class WeeklyGame(BaseModel):
    team_a: str
    team_b: str
    status: str  # final | live | upcoming
    start_time: str  # ISO8601 UTC
    start_time_finnish: str | None = None  # Formatted Finnish time for upcoming games
    start_date_time_finnish: str | None = None  # Full date and time in Finnish
    game_time: str | None = None  # Game clock/period for live games
    score_a: int | None = None
    score_b: int | None = None


class TeamInfo(BaseModel):
    team: str
    abbreviation: str


@app.get("/")
def read_root():
    return {
        "service": "light-score-backend",
        "status": "ok",
        "endpoints": [
            "/games",
            "/standings",
            "/standings/live",
        ],
    }


@app.get("/games", response_model=List[Game])
def get_games():
    raise HTTPException(
        status_code=501, detail="Endpoint deprecated - use /games/weekly"
    )


_GAMES_TTL_SECONDS = 60
# Cache per URL key -> (ts, data)
_games_cache: dict[str, tuple[float, list[dict]]] = {}


def _extract_weekly_games_from_scoreboard(payload: dict) -> list[dict]:
    events = payload.get("events", []) or []
    result: list[dict] = []
    for ev in events:
        date = ev.get("date")
        comps = ev.get("competitions") or []
        if not comps:
            continue
        comp = comps[0] or {}
        status_state = comp.get("status", {}).get("type", {}).get("state") or ev.get(
            "status", {}
        ).get("type", {}).get("state")
        state = (status_state or "").lower()
        if state == "in":
            status = "live"
        elif state == "post":
            status = "final"
        else:
            status = "upcoming"

        competitors = comp.get("competitors") or []
        if len(competitors) < 2:
            continue
        # Ensure away as team_a and home as team_b for consistent ordering
        away = next(
            (c for c in competitors if c.get("homeAway") == "away"), competitors[0]
        )
        home = next(
            (c for c in competitors if c.get("homeAway") == "home"), competitors[1]
        )

        def name_from(c: dict) -> str:
            t = c.get("team", {})
            return (
                t.get("displayName")
                or t.get("shortDisplayName")
                or t.get("name")
                or "Unknown"
            )

        def score_from(c: dict) -> int | None:
            s = c.get("score")
            if s is None:
                return None
            try:
                return int(float(s))
            except Exception:
                return None

        # Generate time fields based on status
        start_time_finnish = None
        start_date_time_finnish = None
        game_time = None

        if status == "upcoming" and date:
            start_time_finnish = format_finnish_time(date)
            start_date_time_finnish = format_finnish_date_time(date)
        elif status == "live":
            game_time = extract_game_time(comp)

        result.append(
            {
                "team_a": name_from(away),
                "team_b": name_from(home),
                "score_a": score_from(away),
                "score_b": score_from(home),
                "status": status,
                "start_time": date,
                "start_time_finnish": start_time_finnish,
                "start_date_time_finnish": start_date_time_finnish,
                "game_time": game_time,
            }
        )
    return result


def _get_weekly_games(
    *,
    year: int | None,
    week: int | None,
    season_type: int | None,
    force_refresh: bool = False,
) -> list[dict]:
    now = time.monotonic()
    base_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    # Build URL with params only when provided
    params: list[str] = []
    if year is not None:
        params.append(f"year={year}")
    if week is not None:
        params.append(f"week={week}")
    if season_type is not None:
        params.append(f"seasontype={season_type}")
    url = base_url + ("?" + "&".join(params) if params else "")

    # Cache key is the full URL
    if not force_refresh and url in _games_cache:
        ts, data = _games_cache[url]
        if (now - ts) < _GAMES_TTL_SECONDS:
            return data

    try:
        resp = httpx.get(url, timeout=20)
        resp.raise_for_status()

        data = resp.json()
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict response, got {type(data)}")
        games = _extract_weekly_games_from_scoreboard(data)
        if games:
            _games_cache[url] = (now, games)
            return games
        # If ESPN returns empty, return empty list
        if url in _games_cache:
            return _games_cache[url][1]
        return []
    except httpx.TimeoutException:
        if url in _games_cache:
            return _games_cache[url][1]
        raise HTTPException(status_code=504, detail="ESPN API timeout") from None
    except httpx.HTTPStatusError as exc:
        if url in _games_cache:
            return _games_cache[url][1]
        status = exc.response.status_code if exc.response is not None else 502
        raise HTTPException(
            status_code=502, detail=f"ESPN API error: {status}"
        ) from exc
    except httpx.RequestError as exc:
        if url in _games_cache:
            return _games_cache[url][1]
        raise HTTPException(status_code=502, detail="ESPN API request failed") from exc
    except Exception as exc:
        if url in _games_cache:
            return _games_cache[url][1]
        raise HTTPException(
            status_code=500, detail="Unexpected error fetching games"
        ) from exc


@app.get("/games/weekly", response_model=List[WeeklyGame])
def get_weekly_games(
    year: int | None = Query(default=None, description="Season year, e.g., 2025"),
    week: int | None = Query(default=None, ge=1, le=25, description="Week number"),
    seasonType: int | None = Query(
        default=None, description="Season type: 1=pre, 2=reg, 3=post"
    ),
):
    return _get_weekly_games(year=year, week=week, season_type=seasonType)


class WeeklyContext(BaseModel):
    year: int
    week: int
    seasonType: int


class NavigationParams(BaseModel):
    year: int
    week: int
    seasonType: int


def get_season_navigation(
    year: int, week: int, season_type: int, direction: str
) -> dict:
    """Calculate navigation parameters with smart season type transitions."""
    # NFL Season Structure (approximate):
    # Preseason (type 1): weeks 1-4
    # Regular Season (type 2): weeks 1-18
    # Postseason (type 3): weeks 1-4

    season_limits = {
        1: (1, 4),  # Preseason: weeks 1-4
        2: (1, 18),  # Regular season: weeks 1-18
        3: (1, 4),  # Postseason: weeks 1-4
    }

    min_week, max_week = season_limits.get(season_type, (1, 18))

    if direction == "next":
        if week < max_week:
            # Stay in current season type, increment week
            return {"year": year, "week": week + 1, "seasonType": season_type}
        else:
            # End of current season type, move to next
            if season_type == 1:  # Preseason -> Regular season
                return {"year": year, "week": 1, "seasonType": 2}
            elif season_type == 2:  # Regular season -> Postseason
                return {"year": year, "week": 1, "seasonType": 3}
            else:  # Postseason -> Next year preseason
                return {"year": year + 1, "week": 1, "seasonType": 1}

    elif direction == "prev":
        if week > min_week:
            # Stay in current season type, decrement week
            return {"year": year, "week": week - 1, "seasonType": season_type}
        else:
            # Beginning of current season type, move to previous
            if season_type == 1:  # Preseason -> Previous year postseason
                return {"year": year - 1, "week": 4, "seasonType": 3}
            elif season_type == 2:  # Regular season -> Preseason
                return {"year": year, "week": 4, "seasonType": 1}
            else:  # Postseason -> Regular season
                return {"year": year, "week": 18, "seasonType": 2}

    # Fallback
    return {"year": year, "week": week, "seasonType": season_type}


def _extract_weekly_context(payload: dict) -> dict:
    season = payload.get("season") or {}
    year = season.get("year")
    s_type = season.get("type")
    week = (payload.get("week") or {}).get("number")
    # Be defensive: ensure ints and validate ranges
    try:
        year = int(year) if year is not None else 2025  # Current NFL season
        s_type = int(s_type) if s_type is not None else 2  # Regular season default
        week = int(week) if week is not None else 1  # Week 1 default

        # Validate ranges
        if year < 1970 or year > 2030:  # Reasonable NFL year range
            year = 2025
        if s_type not in [1, 2, 3]:  # Valid season types only
            s_type = 2
        if (
            week < 1 or week > 25
        ):  # Valid week range (max possible across all season types)
            week = 1

    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="Invalid upstream context") from exc
    return {"year": year, "week": week, "seasonType": s_type}


@app.get("/games/weekly/context", response_model=WeeklyContext)
def get_weekly_context(
    year: int | None = Query(default=None),
    week: int | None = Query(default=None),
    seasonType: int | None = Query(default=None),
):
    base_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    params: list[str] = []
    if year is not None:
        params.append(f"year={year}")
    if week is not None:
        params.append(f"week={week}")
    if seasonType is not None:
        params.append(f"seasontype={seasonType}")
    url = base_url + ("?" + "&".join(params) if params else "")
    try:
        resp = httpx.get(url, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=502, detail="Unexpected upstream format")
        return _extract_weekly_context(payload)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="ESPN API timeout") from None
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        raise HTTPException(
            status_code=502, detail=f"ESPN API error: {status}"
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="ESPN API request failed") from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail="Unexpected error fetching context"
        ) from exc


@app.get("/games/weekly/navigation")
def get_navigation_params(
    year: int = Query(description="Current year"),
    week: int = Query(description="Current week"),
    seasonType: int = Query(
        description="Current season type (1=preseason, 2=regular, 3=postseason)"
    ),
    direction: str = Query(description="Navigation direction: 'next' or 'prev'"),
):
    """Get smart navigation parameters that handle season type transitions."""
    if direction not in ["next", "prev"]:
        raise HTTPException(
            status_code=400, detail="Direction must be 'next' or 'prev'"
        )

    return get_season_navigation(year, week, seasonType, direction)


_TEAMS_TTL_SECONDS = 86400
_teams_cache_ts: float | None = None
_teams_cache_data: list[dict] | None = None


def _extract_teams(payload: dict) -> list[dict]:
    # Expected structure: sports[0].leagues[0].teams -> [{team: {...}}, ...]
    sports = payload.get("sports", [])
    if not sports:
        return []
    leagues = sports[0].get("leagues", [])
    if not leagues:
        return []
    teams = leagues[0].get("teams", []) or []
    res: list[dict] = []
    for t in teams:
        info = (t or {}).get("team", {})
        abbr = info.get("abbreviation")
        name = info.get("displayName") or info.get("name")
        if name and abbr:
            res.append({"team": name, "abbreviation": abbr})
    return res


def _get_all_teams(force_refresh: bool = False) -> list[dict]:
    global _teams_cache_ts, _teams_cache_data
    now = time.monotonic()
    if (
        not force_refresh
        and _teams_cache_data is not None
        and _teams_cache_ts is not None
        and (now - _teams_cache_ts) < _TEAMS_TTL_SECONDS
    ):
        return _teams_cache_data

    try:
        resp = httpx.get(
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams",
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        teams = _extract_teams(data)
        if teams:
            _teams_cache_data = teams
            _teams_cache_ts = now
            return teams
        if _teams_cache_data is not None:
            return _teams_cache_data
        return []
    except httpx.TimeoutException:
        if _teams_cache_data is not None:
            return _teams_cache_data
        return []
    except httpx.HTTPStatusError:
        if _teams_cache_data is not None:
            return _teams_cache_data
        return []
    except httpx.RequestError:
        if _teams_cache_data is not None:
            return _teams_cache_data
        return []
    except Exception:
        if _teams_cache_data is not None:
            return _teams_cache_data
        return []


@app.get("/teams", response_model=List[TeamInfo])
def get_teams():
    return _get_all_teams()


@app.get("/standings", response_model=List[Standings])
def get_standings():
    # Serve from cache file if available; otherwise return error
    cache_file = Path(__file__).resolve().parent / "data" / "standings_cache.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            # Corrupt cache or IO error
            raise HTTPException(
                status_code=500, detail="Standings cache is corrupted"
            ) from exc
    else:
        raise HTTPException(
            status_code=503, detail="Standings data not available - cache file missing"
        )


# --- Live standings (simple TTL cache) ---
_LIVE_TTL_SECONDS = 300
_live_cache_ts: float | None = None
_live_cache_data: list[dict] | None = None


def _extract_minimal_standings(payload: dict) -> list[dict]:
    # ESPN: content.standings.groups -> [AFC, NFC]
    groups = payload.get("content", {}).get("standings", {}).get("groups", [])
    result: list[dict] = []

    def add_entries(entries: list[dict], division_name: str | None):
        for e in entries:
            team = e.get("team", {}).get("displayName")
            stats = {s.get("name"): s for s in e.get("stats", [])}
            wins = stats.get("wins", {}).get("value")
            losses = stats.get("losses", {}).get("value")
            if team is not None and wins is not None and losses is not None:
                # values can be strings or numbers
                try:
                    wins_int = int(float(wins))
                    losses_int = int(float(losses))
                except (ValueError, TypeError):
                    # Skip entries with unparseable stats
                    continue
                result.append(
                    {
                        "team": team,
                        "wins": wins_int,
                        "losses": losses_int,
                        "division": division_name,
                    }
                )

    for conf in groups:
        subgroups = conf.get("groups") or []
        for g in subgroups:
            entries = g.get("standings", {}).get("entries") or []
            division_name = (
                g.get("name") or g.get("abbreviation") or g.get("shortName") or None
            )
            add_entries(entries, division_name)

    return result


def _get_live_standings(force_refresh: bool = False) -> list[dict]:
    global _live_cache_ts, _live_cache_data
    now = time.monotonic()
    if (
        not force_refresh
        and _live_cache_data is not None
        and _live_cache_ts is not None
        and (now - _live_cache_ts) < _LIVE_TTL_SECONDS
    ):
        return _live_cache_data

    try:
        resp = httpx.get("https://cdn.espn.com/core/nfl/standings?xhr=1", timeout=20)
        resp.raise_for_status()
        data = resp.json()
        minimal = _extract_minimal_standings(data)
        _live_cache_data = minimal
        _live_cache_ts = now
        return minimal
    except httpx.TimeoutException:
        # Return stale cache if we have one; otherwise 504
        if _live_cache_data is not None:
            return _live_cache_data
        raise HTTPException(status_code=504, detail="Upstream timeout") from None
    except httpx.HTTPStatusError as exc:
        if _live_cache_data is not None:
            return _live_cache_data
        status = exc.response.status_code if exc.response is not None else 502
        raise HTTPException(
            status_code=502, detail=f"Upstream error: {status}"
        ) from None
    except httpx.RequestError:
        if _live_cache_data is not None:
            return _live_cache_data
        raise HTTPException(status_code=502, detail="Upstream request failed") from None
    except Exception:
        if _live_cache_data is not None:
            return _live_cache_data
        raise HTTPException(status_code=500, detail="Unexpected error") from None


@app.get("/standings/live", response_model=List[Standings])
def get_standings_live():
    return _get_live_standings()
