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
                                                {"name": "ties", "value": "1"},
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
    for row in data:
        if row["team"] == "Mock Team":
            assert row["ties"] == 1


@patch("httpx.get")
def test_live_standings_missing_ties_defaults_zero(mock_get):
    payload = _espn_payload("Another Team")
    entries = payload["content"]["standings"]["groups"][0]["groups"][0]["standings"][
        "entries"
    ]
    entries[0]["stats"] = [
        {"name": "wins", "value": "2"},
        {"name": "losses", "value": "2"},
    ]
    mock_get.return_value.json.return_value = payload
    mock_get.return_value.raise_for_status.return_value = None

    from .. import main as backend_main

    backend_main._live_cache_ts = None
    backend_main._live_cache_data = None

    r = client.get("/standings/live")
    assert r.status_code == 200
    data = r.json()
    target = next(item for item in data if item["team"] == "Another Team")
    assert target["ties"] == 0


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
