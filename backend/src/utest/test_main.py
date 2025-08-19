from fastapi.testclient import TestClient

from ..main import _extract_weekly_games_from_scoreboard, app

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("service") == "light-score-backend"
    assert payload.get("status") == "ok"
    assert "/games" in payload.get("endpoints", [])


def test_get_games():
    response = client.get("/games")
    assert response.status_code == 501  # Endpoint deprecated
    payload = response.json()
    assert (
        "deprecated" in payload["detail"].lower() or "use" in payload["detail"].lower()
    )


def test_get_standings():
    response = client.get("/standings")
    # Should return 503 since cache file doesn't exist in test environment
    assert response.status_code == 503


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
