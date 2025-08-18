from unittest.mock import patch

from fastapi.testclient import TestClient

from ..main import app

client = TestClient(app)


def _espn_payload(team_name: str = "Example Team"):
    return {
        "content": {
            "standings": {
                "groups": [
                    {
                        "abbreviation": "AFC",
                        "groups": [
                            {
                                "standings": {
                                    "entries": [
                                        {
                                            "team": {"displayName": team_name},
                                            "stats": [
                                                {"name": "wins", "value": "3"},
                                                {"name": "losses", "value": "1"},
                                            ],
                                        }
                                    ]
                                }
                            }
                        ],
                    }
                ]
            }
        }
    }


@patch("httpx.get")
def test_live_standings_minimal(mock_get):
    mock_get.return_value.json.return_value = _espn_payload("Mock Team")
    mock_get.return_value.raise_for_status.return_value = None

    r = client.get("/standings/live")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(d["team"] == "Mock Team" for d in data)


@patch("httpx.get")
def test_weekly_games_from_scoreboard(mock_get):
    from .test_main import _scoreboard_payload

    mock_get.return_value.json.return_value = _scoreboard_payload()
    mock_get.return_value.raise_for_status.return_value = None

    r = client.get("/games/weekly")
    assert r.status_code == 200
    data = r.json()
    assert any(g["status"] == "live" for g in data)
    assert any(g["team_a"] == "Away Team" and g["team_b"] == "Home Team" for g in data)


@patch("httpx.get")
def test_teams_from_espn(mock_get):
    from .test_main import _teams_payload

    mock_get.return_value.json.return_value = _teams_payload()
    mock_get.return_value.raise_for_status.return_value = None

    r = client.get("/teams")
    assert r.status_code == 200
    data = r.json()
    assert {"team": "Mock Team", "abbreviation": "MT"} in data
