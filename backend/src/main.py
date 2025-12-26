"""
Light Score Backend API

API Design Notes:
- Query parameters use camelCase (e.g., seasonType, startTime) to match ESPN API
  conventions and JavaScript/JSON naming standards for frontend compatibility.
- Internal Python code uses snake_case per PEP 8 conventions.
- This is an intentional design choice for API consistency with external services.
"""

import json
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
            "/playoffs/picture",
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

    # In production, this would fetch from ESPN's playoff bracket API
    # For now, return empty bracket when not mocking
    return empty_bracket


@app.get("/playoffs/bracket", response_model=PlayoffBracket)
def get_playoff_bracket():
    """Get the playoff bracket with seeds and game results."""
    return _get_playoff_bracket()


# --- Playoff Picture (Race + Status) ---
class PlayoffTeamStatus(BaseModel):
    team: str
    abbreviation: str
    conference: str
    division: str
    wins: int
    losses: int
    ties: int = 0
    games_remaining: int = 0  # Remaining regular season games
    max_possible_wins: int = 0  # Wins + remaining games
    seed: int | None = None  # Current/projected seed (1-7 if in playoffs)
    status: str  # "clinched_bye", "clinched_division", "clinched_wildcard",
    # "in_position", "in_hunt", "eliminated", "alive", "super_bowl"
    status_detail: str  # Human-readable status
    eliminated_round: str | None = (
        None  # For postseason: "Wild Card", "Divisional", etc.
    )
    playoff_wins: int = 0
    playoff_losses: int = 0


class PlayoffPicture(BaseModel):
    season_year: int
    season_type: int  # 2=regular, 3=postseason
    week: int
    afc_teams: List[PlayoffTeamStatus]
    nfc_teams: List[PlayoffTeamStatus]
    super_bowl_teams: List[str]  # Teams in Super Bowl (0-2)


def _compute_playoff_picture_from_standings(standings: list[dict]) -> dict:
    """Compute playoff picture from standings data during regular season.

    NFL Playoff Seeding (per operations.nfl.com/the-rules/nfl-tie-breaking-procedures):
    1. Division champion with best record
    2. Division champion with second-best record
    3. Division champion with third-best record
    4. Division champion with fourth-best record
    5. Wild card club with best record
    6. Wild card club with second-best record
    7. Wild card club with third-best record

    Note: Full NFL tiebreaker rules are complex (head-to-head, division record,
    common games, conference record, strength of victory, etc.). This implementation
    uses a simplified wins-losses-name tiebreaker for display purposes.
    """
    # NFL regular season is 17 games
    TOTAL_GAMES = 17
    PLAYOFF_SPOTS = 7
    DIVISION_WINNER_SPOTS = 4
    WILD_CARD_SPOTS = 3

    # Group by conference and division
    afc_teams = []
    nfc_teams = []

    for team in standings:
        division = team.get("division", "")
        conf = "AFC" if division.startswith("AFC") else "NFC"
        wins = team.get("wins", 0)
        losses = team.get("losses", 0)
        ties = team.get("ties", 0)
        games_played = wins + losses + ties
        games_remaining = max(0, TOTAL_GAMES - games_played)
        max_possible_wins = wins + games_remaining

        team_status = {
            "team": team.get("team", "Unknown"),
            "abbreviation": _get_team_abbrev(team.get("team", "")),
            "conference": conf,
            "division": division,
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "games_remaining": games_remaining,
            "max_possible_wins": max_possible_wins,
            "seed": None,
            "status": "in_hunt",
            "status_detail": "In the hunt",
            "eliminated_round": None,
            "playoff_wins": 0,
            "playoff_losses": 0,
        }

        if conf == "AFC":
            afc_teams.append(team_status)
        else:
            nfc_teams.append(team_status)

    def sort_key(t: dict) -> tuple:
        """Sort teams by wins (desc), losses (asc), then team name alphabetically."""
        return (-t["wins"], t["losses"], t["team"])

    def get_division_leaders(teams: list[dict]) -> dict[str, dict]:
        """Get the best team in each division."""
        divisions: dict[str, list[dict]] = {}
        for team in teams:
            div = team["division"]
            if div not in divisions:
                divisions[div] = []
            divisions[div].append(team)

        leaders = {}
        for div, div_teams in divisions.items():
            div_teams.sort(key=sort_key)
            if div_teams:
                leaders[div] = div_teams[0]
        return leaders

    def assign_playoff_status(teams: list[dict]) -> list[dict]:
        """Assign playoff status using proper NFL seeding rules.

        Seeds 1-4: Division winners sorted by record
        Seeds 5-7: Best non-division-winners (wild cards)
        """
        if len(teams) < PLAYOFF_SPOTS:
            return teams

        # Identify division leaders
        division_leaders = get_division_leaders(teams)
        leader_names = {t["team"] for t in division_leaders.values()}

        # Separate division winners from wild card contenders
        div_winners = [t for t in teams if t["team"] in leader_names]
        non_winners = [t for t in teams if t["team"] not in leader_names]

        # Sort each group by record
        div_winners.sort(key=sort_key)
        non_winners.sort(key=sort_key)

        # Calculate reference points for clinching/elimination
        if len(non_winners) >= WILD_CARD_SPOTS:
            # 7th seed is the 3rd wild card
            seventh_place = non_winners[WILD_CARD_SPOTS - 1]
            seventh_place_wins = seventh_place["wins"]
        else:
            seventh_place_wins = 0

        # 8th place (first team out) for clinching calculation
        if len(non_winners) > WILD_CARD_SPOTS:
            eighth_place_max = non_winners[WILD_CARD_SPOTS]["max_possible_wins"]
        else:
            eighth_place_max = 0

        # Assign seeds to division winners (1-4)
        for i, team in enumerate(div_winners[:DIVISION_WINNER_SPOTS]):
            team["seed"] = i + 1
            # Division winner has clinched if they lead their division
            # (simplified: if they're the division leader, they've clinched division)
            div_second_place = [
                t
                for t in teams
                if t["division"] == team["division"] and t["team"] != team["team"]
            ]
            div_second_max = max(
                (t["max_possible_wins"] for t in div_second_place), default=0
            )

            if team["wins"] > div_second_max:
                if i == 0:
                    team["status"] = "clinched_bye"
                    team["status_detail"] = "Clinched #1 seed"
                else:
                    team["status"] = "clinched_division"
                    team["status_detail"] = f"Clinched division (#{i + 1} seed)"
            else:
                team["status"] = "in_position"
                team["status_detail"] = f"Division leader (#{i + 1} seed)"

        # Assign seeds to wild cards (5-7)
        for i, team in enumerate(non_winners[:WILD_CARD_SPOTS]):
            seed = DIVISION_WINNER_SPOTS + i + 1
            team["seed"] = seed

            # Wild card has clinched if wins > 8th place max possible
            if team["wins"] > eighth_place_max:
                team["status"] = "clinched_wildcard"
                team["status_detail"] = f"Clinched wild card (#{seed} seed)"
            else:
                team["status"] = "in_position"
                team["status_detail"] = f"Wild card (#{seed} seed)"

        # Assign status to teams outside playoffs
        for team in non_winners[WILD_CARD_SPOTS:]:
            # First check: can this team still win their division?
            # If yes, they have a path to playoffs via division title
            div_leader = division_leaders.get(team["division"])
            can_win_division = (
                div_leader is not None
                and team["max_possible_wins"] >= div_leader["wins"]
            )

            if can_win_division:
                # Team can still win division - they're in the hunt
                games_back = div_leader["wins"] - team["wins"]
                if games_back > 0:
                    team["status"] = "in_hunt"
                    team["status_detail"] = (
                        f"{games_back} game{'s' if games_back > 1 else ''} back in division"
                    )
                else:
                    team["status"] = "in_hunt"
                    team["status_detail"] = "In division race"
                continue

            # Team cannot win division - must compete for wild card
            # Per NFL rules, elimination is only when there's NO mathematical path
            #
            # Count teams STRICTLY ahead (wins > max) - can't catch these
            # Count teams at same level (wins == max) - would need tiebreaker
            strictly_ahead = sum(
                1
                for other in non_winners
                if other["team"] != team["team"]
                and other["wins"] > team["max_possible_wins"]
            )
            at_same_level = sum(
                1
                for other in non_winners
                if other["team"] != team["team"]
                and other["wins"] == team["max_possible_wins"]
            )

            # Eliminated: 3+ teams are STRICTLY ahead (can't even tie them)
            # Slim chances: can only tie some teams, needs tiebreaker help
            # In hunt: realistic path exists
            if strictly_ahead >= WILD_CARD_SPOTS:
                # 3+ teams have more wins than our max - no path
                team["status"] = "eliminated"
                team["status_detail"] = "Eliminated from playoffs"
            elif strictly_ahead + at_same_level >= WILD_CARD_SPOTS:
                # Can tie some teams but 3+ total are at or ahead
                # Need help + tiebreaker wins - very slim chances
                team["status"] = "in_hunt"
                team["status_detail"] = "Long shot (needs help + tiebreakers)"
            elif team["max_possible_wins"] < seventh_place_wins:
                # Can't reach current 7th place
                team["status"] = "eliminated"
                team["status_detail"] = "Eliminated from playoffs"
            else:
                games_back = seventh_place_wins - team["wins"]
                if games_back > 0:
                    team["status"] = "in_hunt"
                    team["status_detail"] = (
                        f"{games_back} game{'s' if games_back > 1 else ''} back"
                    )
                else:
                    team["status"] = "in_hunt"
                    team["status_detail"] = "In wild card hunt"

        # Return teams sorted by seed, then by status
        seeded = [t for t in teams if t["seed"] is not None]
        seeded.sort(key=lambda t: t["seed"] or 99)
        unseeded = [t for t in teams if t["seed"] is None]
        unseeded.sort(key=sort_key)
        return seeded + unseeded

    afc_teams = assign_playoff_status(afc_teams)
    nfc_teams = assign_playoff_status(nfc_teams)

    return {
        "afc_teams": afc_teams,
        "nfc_teams": nfc_teams,
    }


def _compute_playoff_picture_from_bracket(bracket: dict) -> dict:
    """Compute playoff picture from bracket data during postseason."""
    afc_teams = []
    nfc_teams = []

    afc_seeds = bracket.get("afc_seeds", [])
    nfc_seeds = bracket.get("nfc_seeds", [])
    games = bracket.get("games", [])

    # Find Super Bowl teams
    super_bowl_teams = []
    for game in games:
        if game.get("conference") == "Super Bowl":
            if game.get("home_team"):
                super_bowl_teams.append(game["home_team"])
            if game.get("away_team"):
                super_bowl_teams.append(game["away_team"])

    # Process AFC seeds
    for seed_info in afc_seeds:
        team_name = seed_info.get("team", "")
        eliminated = seed_info.get("eliminated", False)

        # Find elimination round
        elim_round = None
        playoff_wins = 0
        playoff_losses = 0

        for game in games:
            if (
                game.get("conference") != "AFC"
                and game.get("conference") != "Super Bowl"
            ):
                continue
            if game.get("status") != "final":
                continue

            home = game.get("home_team", "")
            away = game.get("away_team", "")
            winner = game.get("winner", "")

            if team_name in [home, away]:
                if winner == team_name:
                    playoff_wins += 1
                else:
                    playoff_losses += 1
                    elim_round = game.get("round")

        if team_name in super_bowl_teams:
            status = "super_bowl"
            status_detail = "Super Bowl"
        elif eliminated:
            status = "eliminated"
            status_detail = (
                f"Eliminated in {elim_round}" if elim_round else "Eliminated"
            )
        else:
            status = "alive"
            status_detail = "Still alive"

        afc_teams.append(
            {
                "team": team_name,
                "abbreviation": seed_info.get("abbreviation", ""),
                "conference": "AFC",
                "division": "",
                "wins": 0,
                "losses": 0,
                "ties": 0,
                "seed": seed_info.get("seed"),
                "status": status,
                "status_detail": status_detail,
                "eliminated_round": elim_round,
                "playoff_wins": playoff_wins,
                "playoff_losses": playoff_losses,
            }
        )

    # Process NFC seeds
    for seed_info in nfc_seeds:
        team_name = seed_info.get("team", "")
        eliminated = seed_info.get("eliminated", False)

        elim_round = None
        playoff_wins = 0
        playoff_losses = 0

        for game in games:
            if (
                game.get("conference") != "NFC"
                and game.get("conference") != "Super Bowl"
            ):
                continue
            if game.get("status") != "final":
                continue

            home = game.get("home_team", "")
            away = game.get("away_team", "")
            winner = game.get("winner", "")

            if team_name in [home, away]:
                if winner == team_name:
                    playoff_wins += 1
                else:
                    playoff_losses += 1
                    elim_round = game.get("round")

        if team_name in super_bowl_teams:
            status = "super_bowl"
            status_detail = "Super Bowl"
        elif eliminated:
            status = "eliminated"
            status_detail = (
                f"Eliminated in {elim_round}" if elim_round else "Eliminated"
            )
        else:
            status = "alive"
            status_detail = "Still alive"

        nfc_teams.append(
            {
                "team": team_name,
                "abbreviation": seed_info.get("abbreviation", ""),
                "conference": "NFC",
                "division": "",
                "wins": 0,
                "losses": 0,
                "ties": 0,
                "seed": seed_info.get("seed"),
                "status": status,
                "status_detail": status_detail,
                "eliminated_round": elim_round,
                "playoff_wins": playoff_wins,
                "playoff_losses": playoff_losses,
            }
        )

    return {
        "afc_teams": afc_teams,
        "nfc_teams": nfc_teams,
        "super_bowl_teams": super_bowl_teams,
    }


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
    """Get team abbreviation from full name, with fallback for unknown teams."""
    return _TEAM_ABBREVS.get(team_name, team_name[:3].upper() if team_name else "UNK")


def _get_playoff_picture(season_type: int | None = None) -> dict:
    """Get playoff picture based on season type."""
    # Determine season type from context if not provided
    if season_type is None:
        season_type = 2  # Default to regular season

    if season_type == 3:
        # Postseason: use bracket data
        bracket = _get_playoff_bracket()
        picture = _compute_playoff_picture_from_bracket(bracket)
        return {
            "season_year": bracket.get("season_year", 2024),
            "season_type": 3,
            "week": 1,
            "afc_teams": picture["afc_teams"],
            "nfc_teams": picture["nfc_teams"],
            "super_bowl_teams": picture.get("super_bowl_teams", []),
        }
    else:
        # Regular season: use standings data
        standings = _get_live_standings()
        picture = _compute_playoff_picture_from_standings(standings)
        return {
            "season_year": 2024,
            "season_type": 2,
            "week": 15,
            "afc_teams": picture["afc_teams"],
            "nfc_teams": picture["nfc_teams"],
            "super_bowl_teams": [],
        }


@app.get("/playoffs/picture", response_model=PlayoffPicture)
def get_playoff_picture(
    seasonType: int | None = Query(
        default=None, description="Season type: 2=regular, 3=postseason"
    ),
):
    """Get the playoff picture with team statuses and race standings."""
    return _get_playoff_picture(seasonType)
