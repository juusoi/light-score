import json
import time
from pathlib import Path
from typing import List

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from data.example import example_data

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


class WeeklyGame(BaseModel):
    team_a: str
    team_b: str
    status: str  # final | live | upcoming
    start_time: str  # ISO8601 UTC
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
    return example_data["games"]


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

        result.append(
            {
                "team_a": name_from(away),
                "team_b": name_from(home),
                "score_a": score_from(away),
                "score_b": score_from(home),
                "status": status,
                "start_time": date,
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
        from typing import cast

        data = cast(dict, resp.json())
        games = _extract_weekly_games_from_scoreboard(data)
        if games:
            _games_cache[url] = (now, games)
            return games
        # If ESPN returns empty, fall back to cached or example
        if url in _games_cache:
            return _games_cache[url][1]
        return example_data.get("weekly_games", [])
    except httpx.TimeoutException:
        if url in _games_cache:
            return _games_cache[url][1]
        return example_data.get("weekly_games", [])
    except httpx.HTTPStatusError:
        if url in _games_cache:
            return _games_cache[url][1]
        return example_data.get("weekly_games", [])
    except httpx.RequestError:
        if url in _games_cache:
            return _games_cache[url][1]
        return example_data.get("weekly_games", [])
    except Exception:
        if url in _games_cache:
            return _games_cache[url][1]
        return example_data.get("weekly_games", [])


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


def _extract_weekly_context(payload: dict) -> dict:
    season = payload.get("season") or {}
    year = season.get("year")
    s_type = season.get("type")
    week = (payload.get("week") or {}).get("number")
    # Be defensive: ensure ints
    try:
        year = int(year)
        s_type = int(s_type)
        week = int(week)
    except Exception:
        raise HTTPException(status_code=502, detail="Invalid upstream context")
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
        raise HTTPException(status_code=504, detail="Upstream timeout") from None
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        raise HTTPException(
            status_code=502, detail=f"Upstream error: {status}"
        ) from None
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Upstream request failed") from None


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
    # Serve from cache file if available; fallback to example data
    cache_file = Path(__file__).resolve().parent / "data" / "standings_cache.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            # If cache is corrupt, fall back to example
            pass
    return example_data["standings"]


# --- Live standings (simple TTL cache) ---
_LIVE_TTL_SECONDS = 300
_live_cache_ts: float | None = None
_live_cache_data: list[dict] | None = None


def _extract_minimal_standings(payload: dict) -> list[dict]:
    # ESPN: content.standings.groups -> [AFC, NFC]
    groups = payload.get("content", {}).get("standings", {}).get("groups", [])
    result: list[dict] = []

    def add_entries(entries: list[dict]):
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
                except Exception:
                    continue
                result.append({"team": team, "wins": wins_int, "losses": losses_int})

    for conf in groups:
        subgroups = conf.get("groups") or []
        for g in subgroups:
            entries = g.get("standings", {}).get("entries") or []
            add_entries(entries)

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
