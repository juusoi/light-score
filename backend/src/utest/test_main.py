from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ..main import (  # ty: ignore[unresolved-import]
    _current_nfl_season_year,
    _extract_weekly_context,
    _extract_weekly_games_from_scoreboard,
    _get_weekly_games,
    _scoreboard_matches_requested_context,
    app,
)

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("service") == "light-score-backend"
    assert payload.get("status") == "ok"
    assert "/games/weekly" in payload.get("endpoints", [])


def test_get_standings():
    response = client.get("/standings")
    if response.status_code == 503:
        payload = response.json()
        assert "detail" in payload
        assert "Standings data not available" in payload["detail"]
    else:
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        if payload:
            row = payload[0]
            assert "team" in row and "wins" in row and "losses" in row


def test_get_weekly_games():
    response = client.get("/games/weekly")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        g = data[0]
        assert "team_a" in g and "team_b" in g and "status" in g
        # Test new timezone fields
        assert "start_time_finnish" in g
        assert "start_date_time_finnish" in g
        assert "game_time" in g


def test_weekly_games_timezone_fields():
    """Test that timezone fields are properly included in weekly games."""
    response = client.get("/games/weekly")
    assert response.status_code == 200
    data = response.json()

    for game in data:
        # All games should have these timezone fields
        assert "start_time_finnish" in game
        assert "start_date_time_finnish" in game
        assert "game_time" in game

        # Fields should be None for final games
        if game["status"] == "final":
            assert game["start_time_finnish"] is None
            assert game["start_date_time_finnish"] is None
            assert game["game_time"] is None

        # Live games might have game_time
        if game["status"] == "live":
            assert game["start_time_finnish"] is None
            assert game["start_date_time_finnish"] is None
            # game_time could be present or None depending on ESPN data

        # Upcoming games might have Finnish time fields
        if game["status"] == "upcoming":
            assert game["game_time"] is None
            # start_time_finnish and start_date_time_finnish could be present or None


def _scoreboard_payload():
    return {
        "events": [
            {
                "date": "2025-08-18T16:00:00Z",
                "competitions": [
                    {
                        "status": {"type": {"state": "in"}},
                        "competitors": [
                            {
                                "homeAway": "away",
                                "team": {"displayName": "Away Team"},
                                "score": "13",
                            },
                            {
                                "homeAway": "home",
                                "team": {"displayName": "Home Team"},
                                "score": "16",
                            },
                        ],
                    }
                ],
            }
        ]
    }


def _teams_payload():
    return {
        "sports": [
            {
                "leagues": [
                    {
                        "teams": [
                            {"team": {"displayName": "Mock Team", "abbreviation": "MT"}}
                        ]
                    }
                ]
            }
        ]
    }


def test_get_teams_fallback_empty():
    r = client.get("/teams")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_extract_weekly_games_with_timezone_fields():
    """Test that game extraction includes timezone fields."""
    upcoming_game_payload = {
        "events": [
            {
                "date": "2025-08-19T19:30:00Z",
                "competitions": [
                    {
                        "status": {"type": {"state": "pre"}},  # upcoming
                        "competitors": [
                            {
                                "homeAway": "away",
                                "team": {"displayName": "Away Team"},
                            },
                            {
                                "homeAway": "home",
                                "team": {"displayName": "Home Team"},
                            },
                        ],
                    }
                ],
            }
        ]
    }

    games = _extract_weekly_games_from_scoreboard(upcoming_game_payload)
    assert len(games) == 1

    game = games[0]
    assert game["status"] == "upcoming"
    assert game["start_time"] == "2025-08-19T19:30:00Z"
    assert game["start_time_finnish"] == "22:30"  # UTC+3 summer time
    assert game["start_date_time_finnish"] == "Tue 19.08. 22:30"
    assert game["game_time"] is None


def test_extract_live_game_with_clock():
    """Test extracting live game with game clock."""
    live_game_payload = {
        "events": [
            {
                "date": "2025-08-19T16:00:00Z",
                "competitions": [
                    {
                        "status": {
                            "type": {"state": "in", "name": "STATUS_IN_PROGRESS"},
                            "displayClock": "08:45",
                            "period": 3,
                        },
                        "competitors": [
                            {
                                "homeAway": "away",
                                "team": {"displayName": "Team A"},
                                "score": "14",
                            },
                            {
                                "homeAway": "home",
                                "team": {"displayName": "Team B"},
                                "score": "21",
                            },
                        ],
                    }
                ],
            }
        ]
    }

    games = _extract_weekly_games_from_scoreboard(live_game_payload)
    assert len(games) == 1

    game = games[0]
    assert game["status"] == "live"
    assert game["start_time_finnish"] is None
    assert game["start_date_time_finnish"] is None
    assert game["game_time"] == "Q3 08:45"


def test_extract_final_game():
    """Test extracting final game (no timezone fields should be set)."""
    final_game_payload = {
        "events": [
            {
                "date": "2025-08-15T23:00:00Z",
                "competitions": [
                    {
                        "status": {"type": {"state": "post"}},  # final
                        "competitors": [
                            {
                                "homeAway": "away",
                                "team": {"displayName": "Team A"},
                                "score": "28",
                            },
                            {
                                "homeAway": "home",
                                "team": {"displayName": "Team B"},
                                "score": "17",
                            },
                        ],
                    }
                ],
            }
        ]
    }

    games = _extract_weekly_games_from_scoreboard(final_game_payload)
    assert len(games) == 1

    game = games[0]
    assert game["status"] == "final"
    assert game["start_time_finnish"] is None
    assert game["start_date_time_finnish"] is None
    assert game["game_time"] is None


def test_extract_weekly_context_valid():
    """Test extracting weekly context with valid data."""
    payload = {"season": {"year": 2025, "type": 2}, "week": {"number": 5}}

    context = _extract_weekly_context(payload)
    assert context == {"year": 2025, "week": 5, "seasonType": 2}


def test_extract_weekly_context_missing_data():
    """Test extracting weekly context with missing data uses sensible defaults."""
    payload = {}

    context = _extract_weekly_context(payload)
    assert context == {"year": 2026, "week": 1, "seasonType": 2}


def test_extract_weekly_context_invalid_ranges():
    """Test extracting weekly context with invalid ranges uses sensible defaults."""
    payload = {
        "season": {"year": 1900, "type": 99},  # Invalid year and season type
        "week": {"number": 50},  # Invalid week
    }

    context = _extract_weekly_context(payload)
    assert context == {"year": 2026, "week": 1, "seasonType": 2}


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 1, 15), 2025),  # Jan: prior season's playoffs still running
        (date(2026, 2, 8), 2025),  # early Feb: Super Bowl of the prior season
        (date(2026, 3, 1), 2026),  # Mar: new league year -> season rolls forward
        (date(2026, 7, 21), 2026),  # off-season summer: upcoming season is current
        (date(2026, 9, 10), 2026),  # in-season
        (date(2026, 12, 31), 2026),  # late season
    ],
)
def test_current_nfl_season_year_boundaries(today, expected):
    """Season year flips to the new year in March, matching ESPN's rollover."""
    with patch("src.main.date") as mock_date:
        mock_date.today.return_value = today
        assert _current_nfl_season_year() == expected


def test_scoreboard_matches_requested_context_year_mismatch():
    """Guard rejects a payload whose season year differs from the request."""
    # Mirrors ESPN's off-season fallback: requested 2026 but payload is 2025.
    payload = {"season": {"year": 2025, "type": 2}, "week": {"number": 1}}
    assert not _scoreboard_matches_requested_context(
        payload, year=2026, week=1, season_type=2
    )


def test_scoreboard_matches_requested_context_year_match():
    """Guard accepts a payload whose season context matches the request."""
    payload = {"season": {"year": 2026, "type": 2}, "week": {"number": 1}}
    assert _scoreboard_matches_requested_context(
        payload, year=2026, week=1, season_type=2
    )


def _week1_scoreboard_payload(year: int):
    """Minimal scoreboard payload for regular-season week 1 of the given year."""
    return {
        "season": {"year": year, "type": 2},
        "week": {"number": 1},
        "events": [
            {
                "date": "2026-09-10T23:00:00Z",
                "competitions": [
                    {
                        "status": {"type": {"state": "pre"}},
                        "competitors": [
                            {"homeAway": "away", "team": {"displayName": "Away Team"}},
                            {"homeAway": "home", "team": {"displayName": "Home Team"}},
                        ],
                    }
                ],
            }
        ],
    }


@patch("src.main.MOCK_ESPN", False)
@patch("httpx.get")
def test_weekly_games_explicit_week1_sends_dates_param(mock_get):
    """Regression: explicit ?year=2026&week=1 must send `dates=`, not `year=`.

    ESPN ignores `year=` and falls back to the current season, which makes the
    context guard drop every game ("No games" bug). Sending `dates=YYYY` returns
    the requested season so the guard passes.
    """
    mock_get.return_value.json.return_value = _week1_scoreboard_payload(2026)
    mock_get.return_value.raise_for_status.return_value = None

    games = _get_weekly_games(year=2026, week=1, season_type=2, force_refresh=True)

    # Games are returned rather than an empty "No games" list.
    assert len(games) == 1
    assert games[0]["team_a"] == "Away Team"
    assert games[0]["team_b"] == "Home Team"

    # The ESPN request carries the season year as `dates=`, never `year=`.
    requested_url = mock_get.call_args.args[0]
    assert "dates=2026" in requested_url
    assert "year=2026" not in requested_url
    assert "week=1" in requested_url
    assert "seasontype=2" in requested_url


@patch("src.main.MOCK_ESPN", False)
@patch("httpx.get")
def test_weekly_games_endpoint_returns_games_for_explicit_week1(mock_get):
    """End-to-end via the API: explicit week-1 params return the slate."""
    mock_get.return_value.json.return_value = _week1_scoreboard_payload(2026)
    mock_get.return_value.raise_for_status.return_value = None

    resp = client.get("/games/weekly?year=2026&week=1&seasonType=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["team_a"] == "Away Team"
