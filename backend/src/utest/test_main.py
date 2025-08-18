from fastapi.testclient import TestClient

from ..main import app

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
    assert response.status_code == 200
    # Add more assertions here based on your example_data structure
    # For example:
    assert "team_a" in response.json()[0]
    assert "score_a" in response.json()[0]


def test_get_standings():
    response = client.get("/standings")
    assert response.status_code == 200
    # Similar to the above, add assertions based on your expected data structure
    # Example:
    assert "team" in response.json()[0]
    assert "wins" in response.json()[0]


def test_get_weekly_games():
    response = client.get("/games/weekly")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        g = data[0]
        assert "team_a" in g and "team_b" in g and "status" in g


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
