"""
Light Score Backend API

API Design Notes:
- Query parameters use camelCase (e.g., seasonType, fixture) to match ESPN API
  conventions and JavaScript/JSON naming standards for frontend compatibility.
- Internal Python code uses snake_case per PEP 8 conventions.
- This is an intentional design choice for API consistency with external services.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# Mock ESPN mode for testing
MOCK_ESPN = os.getenv("MOCK_ESPN", "").lower() in ("1", "true")
FIXTURES_PATH = Path(__file__).parent / "fixtures"

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


def _load_fixture(name: str) -> dict | list:
    """Load a JSON fixture file by name."""
    fixture_path = FIXTURES_PATH / f"{name}.json"
    if not fixture_path.exists():
        raise HTTPException(status_code=404, detail=f"Fixture '{name}' not found")
    return json.loads(fixture_path.read_text())


def _detect_fixture_name(
    year: int | None, week: int | None, season_type: int | None
) -> str:
    """Detect which fixture to use based on parameters."""
    # Use season type to determine fixture
    if season_type == 3:  # Postseason
        if week == 1:
            return "postseason_wildcard"
        elif week == 2:
            return "postseason_divisional"
        elif week == 3:
            return "postseason_conference"
        elif week == 4:
            return "postseason_superbowl"
        return "postseason_wildcard"  # Default for postseason
    return "regular_season"  # Default for regular/preseason


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
    ties: int = 0
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
            "/games/weekly",
            "/standings",
            "/standings/live",
            "/playoffs/bracket",
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


ESPN_TIMEOUT_SECONDS = int(os.getenv("ESPN_TIMEOUT_SECONDS", "6"))


def _get_weekly_games(
    *,
    year: int | None,
    week: int | None,
    season_type: int | None,
    force_refresh: bool = False,
    fixture: str | None = None,
) -> list[dict]:
    # Mock mode: load from fixture files
    if MOCK_ESPN:
        fixture_name = fixture or _detect_fixture_name(year, week, season_type)
        fixture_data = _load_fixture(fixture_name)
        if isinstance(fixture_data, dict):
            return fixture_data.get("games", [])
        return []

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
        resp = httpx.get(url, timeout=ESPN_TIMEOUT_SECONDS)
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
    fixture: str | None = Query(
        default=None, description="Mock fixture name (only when MOCK_ESPN=true)"
    ),
):
    return _get_weekly_games(
        year=year, week=week, season_type=seasonType, fixture=fixture
    )


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
    fixture: str | None = Query(default=None),
):
    # Mock mode: extract context from fixture file
    if MOCK_ESPN:
        fixture_name = fixture or _detect_fixture_name(year, week, seasonType)
        fixture_data = _load_fixture(fixture_name)
        if isinstance(fixture_data, dict):
            return {
                "year": fixture_data.get("season", {}).get("year", 2024),
                "week": fixture_data.get("week", {}).get("number", 1),
                "seasonType": fixture_data.get("season", {}).get("type", 2),
            }
        return {"year": 2024, "week": 1, "seasonType": 2}

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
        resp = httpx.get(url, timeout=ESPN_TIMEOUT_SECONDS)
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
            timeout=ESPN_TIMEOUT_SECONDS,
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
            ties = stats.get("ties", {}).get("value")
            if team is not None and wins is not None and losses is not None:
                # values can be strings or numbers
                try:
                    wins_int = int(float(wins))
                    losses_int = int(float(losses))
                except (ValueError, TypeError):
                    # Skip entries with unparseable stats
                    continue
                ties_int = 0
                if ties is not None:
                    try:
                        ties_int = int(float(ties))
                    except (ValueError, TypeError):
                        ties_int = 0
                result.append(
                    {
                        "team": team,
                        "wins": wins_int,
                        "losses": losses_int,
                        "ties": ties_int,
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
    # Mock mode: load from fixture file
    if MOCK_ESPN:
        data = _load_fixture("standings")
        return data if isinstance(data, list) else []

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
        resp = httpx.get(
            "https://cdn.espn.com/core/nfl/standings?xhr=1",
            timeout=ESPN_TIMEOUT_SECONDS,
        )
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


# --- Playoff Bracket ---
class PlayoffSeed(BaseModel):
    seed: int
    team: str
    abbreviation: str
    eliminated: bool


class PlayoffGame(BaseModel):
    round: str  # "Wild Card", "Divisional", "Conference", "Super Bowl"
    round_number: int
    conference: str  # "AFC", "NFC", or "Super Bowl"
    home_team: str
    home_seed: int | None
    home_score: int | None
    away_team: str
    away_seed: int | None
    away_score: int | None
    status: str  # "final", "live", "upcoming"
    winner: str | None


class PlayoffBracket(BaseModel):
    season_year: int
    afc_seeds: List[PlayoffSeed]
    nfc_seeds: List[PlayoffSeed]
    games: List[PlayoffGame]


def _get_team_conference(team_name: str, conf_map: dict) -> str:
    """Determine conference for a team using the standings map."""
    return conf_map.get(team_name, "Unknown")


def _extract_playoff_games(
    payload: dict, week: int, conf_map: dict
) -> tuple[list[dict], dict[str, int]]:
    """Extract games and seeds from a weekly scoreboard payload."""
    events = payload.get("events", []) or []
    games = []
    seeds_found = {}  # Map team_name -> seed

    # Map week number to Round Name
    round_map = {
        1: "Wild Card",
        2: "Divisional",
        3: "Conference",
        4: "Super Bowl",  # Week 4 is typically Pro Bowl week or gap, but handling it
        5: "Super Bowl",
    }
    round_name = round_map.get(week, "Unknown")

    for ev in events:
        comps = ev.get("competitions") or []
        if not comps:
            continue
        comp = comps[0]

        # Filter out Pro Bowl if identified (usually type id != 1 or name contains Pro Bowl)
        # Note: Regular NFL game type id is 1. Postseason is 1 too. Pro Bowl is different.
        # Simple check on name
        name = ev.get("name", "")
        if "Pro Bowl" in name:
            continue

        competitors = comp.get("competitors") or []
        if len(competitors) < 2:
            continue

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

        def seed_from(c: dict) -> int | None:
            # Try curatedRank first
            try:
                rank = c.get("curatedRank", {}).get("current")
                if rank and rank != 99:
                    return int(rank)
            except (ValueError, TypeError):
                pass
            # Fallback (rarely available in simple scoreboard)
            return None

        team_a = name_from(away)
        team_b = name_from(home)
        score_a = score_from(away)
        score_b = score_from(home)
        seed_a = seed_from(away)
        seed_b = seed_from(home)

        if seed_a:
            seeds_found[team_a] = seed_a
        if seed_b:
            seeds_found[team_b] = seed_b

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

        winner = None
        if status == "final":
            if score_a is not None and score_b is not None:
                if score_a > score_b:
                    winner = team_a
                elif score_b > score_a:
                    winner = team_b

        # Determine conference
        # If round is Super Bowl, conference is Super Bowl
        if "Super Bowl" in round_name or week >= 4:
            conference = "Super Bowl"
        else:
            # Use home team's conference usually
            conference = _get_team_conference(team_b, conf_map)
            if conference == "Unknown":
                conference = _get_team_conference(team_a, conf_map)

        games.append(
            {
                "round": round_name,
                "round_number": week,
                "conference": conference,
                "home_team": team_b,
                "home_seed": seed_b,
                "home_score": score_b,
                "away_team": team_a,
                "away_seed": seed_a,
                "away_score": score_a,
                "status": status,
                "winner": winner,
            }
        )

    return games, seeds_found


def _fetch_real_playoff_bracket() -> dict:
    """Fetch real playoff data from ESPN."""
    # 1. Get Context (Year)
    year = 2024
    base_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    try:
        # Quick fetch to get accurate year from default scoreboard
        with httpx.Client() as client:
            resp = client.get(base_url, timeout=4)
            if resp.status_code == 200:
                year = resp.json().get("season", {}).get("year", 2024)
    except Exception:
        pass

    # 2. Get Conference Map from Standings
    # We use _get_live_standings (cached)
    standings = _get_live_standings()
    conf_map = {}
    for team in standings:
        t_name = team.get("team")
        div = team.get("division", "")
        if t_name:
            if div.startswith("AFC"):
                conf_map[t_name] = "AFC"
            elif div.startswith("NFC"):
                conf_map[t_name] = "NFC"

    # 3. Fetch Games for Weeks 1-5
    all_games = []
    all_seeds = {}

    with httpx.Client() as client:
        for week in range(1, 6):
            try:
                params = {"year": year, "seasontype": 3, "week": week}
                resp = client.get(base_url, params=params, timeout=ESPN_TIMEOUT_SECONDS)
                resp.raise_for_status()
                data = resp.json()

                games, seeds = _extract_playoff_games(data, week, conf_map)
                all_games.extend(games)
                all_seeds.update(seeds)
            except Exception as e:
                logging.warning(f"Failed to fetch playoff week {week}: {e}")
                continue

    # 4. Construct Seeds List
    # We need to list all teams that appeared in the bracket
    # Identify elimination status
    team_status = {}  # team -> eliminated?

    # Initialize with False
    for team in all_seeds.keys():
        team_status[team] = False

    # Check games for elimination
    # A team is eliminated if they lost a game
    # EXCEPT for Super Bowl winner? No, bracket usually shows strikethrough for losers.

    super_bowl_teams = set()
    for g in all_games:
        if g["conference"] == "Super Bowl":
            super_bowl_teams.add(g["home_team"])
            super_bowl_teams.add(g["away_team"])

    for g in all_games:
        if g["status"] == "final" and g["winner"]:
            loser = g["home_team"] if g["winner"] == g["away_team"] else g["away_team"]
            team_status[loser] = True

    afc_seeds_list = []
    nfc_seeds_list = []

    for team, seed in all_seeds.items():
        conf = conf_map.get(team, "Unknown")
        entry = {
            "seed": seed,
            "team": team,
            "abbreviation": _get_team_abbrev(team),
            "eliminated": team_status.get(team, False),
        }
        if conf == "AFC":
            afc_seeds_list.append(entry)
        elif conf == "NFC":
            nfc_seeds_list.append(entry)
        # If unknown (e.g. Super Bowl team not in standings cache?), try to infer
        # But usually they are in standings.

    # Sort by seed
    afc_seeds_list.sort(key=lambda x: x["seed"])
    nfc_seeds_list.sort(key=lambda x: x["seed"])

    return {
        "season_year": year,
        "afc_seeds": afc_seeds_list,
        "nfc_seeds": nfc_seeds_list,
        "games": all_games,
    }


def _get_playoff_bracket() -> dict:
    """Get playoff bracket data."""
    empty_bracket: dict = {
        "season_year": 2024,
        "afc_seeds": [],
        "nfc_seeds": [],
        "games": [],
    }
    if MOCK_ESPN:
        data = _load_fixture("playoff_seeds")
        return data if isinstance(data, dict) else empty_bracket

    try:
        return _fetch_real_playoff_bracket()
    except Exception as e:
        logging.error(f"Error fetching real playoff bracket: {e}")
        return empty_bracket


@app.get("/playoffs/bracket", response_model=PlayoffBracket)
def get_playoff_bracket():
    """Get the playoff bracket with seeds and game results."""
    return _get_playoff_bracket()





# Team abbreviation lookup (simplified)
_TEAM_ABBREVS = {
    "Kansas City Chiefs": "KC",
    "Buffalo Bills": "BUF",
    "Baltimore Ravens": "BAL",
    "Houston Texans": "HOU",
    "Los Angeles Chargers": "LAC",
    "Pittsburgh Steelers": "PIT",
    "Denver Broncos": "DEN",
    "Miami Dolphins": "MIA",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Tennessee Titans": "TEN",
    "Las Vegas Raiders": "LV",
    "New York Jets": "NYJ",
    "New England Patriots": "NE",
    "Detroit Lions": "DET",
    "Philadelphia Eagles": "PHI",
    "Los Angeles Rams": "LAR",
    "Tampa Bay Buccaneers": "TB",
    "Minnesota Vikings": "MIN",
    "Washington Commanders": "WAS",
    "Green Bay Packers": "GB",
    "Seattle Seahawks": "SEA",
    "San Francisco 49ers": "SF",
    "Dallas Cowboys": "DAL",
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "New Orleans Saints": "NO",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "New York Giants": "NYG",
}


def _get_team_abbrev(team_name: str) -> str:
    """Get team abbreviation from full name, with fallback for unknown teams.

    The fallback scenario would occur in production when:
    - ESPN API returns a team name not in our lookup table (e.g., future expansion teams)
    - ESPN uses a different naming convention than expected (e.g., "LA Rams" vs "Los Angeles Rams")
    - Malformed or unexpected data from ESPN API

    In mock mode, this could occur if fixture data uses team names not matching
    the _TEAM_ABBREVS lookup table.

    When fallback is used, a WARNING is logged to aid debugging and help identify
    missing team mappings that should be added to _TEAM_ABBREVS.
    """
    if team_name in _TEAM_ABBREVS:
        return _TEAM_ABBREVS[team_name]

    # Fallback: use first 3 characters, or "UNK" for empty names
    fallback = team_name[:3].upper() if team_name else "UNK"

    # Log warning to help identify missing team mappings.
    # Note: fallback may be confusing (e.g., "Los Angeles Rams" -> "LOS" not "LAR")
    logging.warning(
        "Unknown team name '%s', using fallback abbreviation '%s'. "
        "Consider adding this team to _TEAM_ABBREVS.",
        team_name,
        fallback,
    )
    return fallback



