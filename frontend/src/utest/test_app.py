from unittest.mock import MagicMock, patch

import pytest
import requests

from ..app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_home_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Light Score" in response.data


@patch("requests.get")
def test_home_route_with_navigation_params(mock_get, client):
    mock_weekly_response = MagicMock(ok=True)
    mock_weekly_response.json.return_value = [
        {
            "team_a": "Team 1",
            "team_b": "Team 2",
            "status": "upcoming",
            "start_time": "2025-08-19T19:30:00Z",
            "start_time_finnish": "22:30",
            "start_date_time_finnish": "Tue 19.08. 22:30",
            "game_time": None,
            "score_a": None,
            "score_b": None,
        }
    ]
    mock_context_response = MagicMock(ok=True)
    mock_context_response.json.return_value = {
        "year": 2025,
        "week": 3,
        "seasonType": 1,
    }
    mock_standings_response = MagicMock(ok=True)
    mock_standings_response.json.return_value = [
        {"team": "Team 1", "wins": 2, "losses": 0, "division": "AFC East"}
    ]
    mock_nav_response = MagicMock(ok=True)
    mock_nav_response.json.return_value = {"year": 2025, "week": 2, "seasonType": 1}

    def mock_get_side_effect(url, **kwargs):
        if "weekly" in url and "context" not in url:
            return mock_weekly_response
        elif "context" in url:
            return mock_context_response
        elif "standings/live" in url:
            return mock_standings_response
        elif "navigation" in url:
            return mock_nav_response
        else:
            return MagicMock(ok=False)

    mock_get.side_effect = mock_get_side_effect

    response = client.get("/?year=2025&seasonType=1&week=3")
    assert response.status_code == 200
    body = response.data
    assert b"Light Score" in body
    assert b"Prev" in body
    assert b"Next" in body
    assert b"Week 3" in body


@patch("requests.get")
def test_navigation_parameters_in_response(mock_get, client):
    mock_weekly_response = MagicMock(ok=True)
    mock_weekly_response.json.return_value = []
    mock_context_response = MagicMock(ok=True)
    mock_context_response.json.return_value = {
        "year": 2025,
        "week": 1,
        "seasonType": 2,
    }
    mock_standings_response = MagicMock(ok=True)
    mock_standings_response.json.return_value = []
    mock_nav_response = MagicMock(ok=True)
    mock_nav_response.json.return_value = {"year": 2025, "week": 2, "seasonType": 2}

    def mock_get_side_effect(url, **kwargs):
        if "weekly" in url and "context" not in url:
            return mock_weekly_response
        elif "context" in url:
            return mock_context_response
        elif "standings/live" in url:
            return mock_standings_response
        elif "navigation" in url:
            return mock_nav_response
        else:
            return MagicMock(ok=False)

    mock_get.side_effect = mock_get_side_effect

    response = client.get("/?year=2025&seasonType=2&week=1")
    assert response.status_code == 200
    text = response.data.decode("utf-8")
    assert "Prev" in text
    assert "Next" in text
    assert "Week 1" in text


@patch("requests.get")
def test_schedule_panel_shows_final_and_upcoming(mock_get, client):
    weekly = [
        {
            "team_a": "A",
            "team_b": "B",
            "status": "final",
            "start_time": "2025-08-10T18:00:00Z",
            "start_time_finnish": None,
            "start_date_time_finnish": None,
            "game_time": None,
            "score_a": 21,
            "score_b": 17,
        },
        {
            "team_a": "C",
            "team_b": "D",
            "status": "upcoming",
            "start_time": "2025-08-11T18:00:00Z",
            "start_time_finnish": "21:00",
            "start_date_time_finnish": "Mon 11.08. 21:00",
            "game_time": None,
            "score_a": None,
            "score_b": None,
        },
    ]
    ctx_json = {"year": 2025, "week": 4, "seasonType": 2}
    standings_json = []
    nav_json = {"year": 2025, "week": 3, "seasonType": 2}

    def side_effect(url, **kwargs):
        if url.endswith("/games/weekly"):
            r = MagicMock(ok=True)
            r.json.return_value = weekly
            return r
        elif url.endswith("/games/weekly/context"):
            r = MagicMock(ok=True)
            r.json.return_value = ctx_json
            return r
        elif url.endswith("/standings/live"):
            r = MagicMock(ok=True)
            r.json.return_value = standings_json
            return r
        elif "/navigation" in url:
            r = MagicMock(ok=True)
            r.json.return_value = nav_json
            return r
        else:
            return MagicMock(ok=False)

    mock_get.side_effect = side_effect
    resp = client.get("/?year=2025&seasonType=2&week=4")
    assert resp.status_code == 200
    text = resp.data.decode()
    assert "Schedule" in text
    assert "A vs B" in text
    assert "21 - 17" in text
    assert "C vs D" in text
    assert "Mon 11.08." in text or "21:00" in text


@patch("requests.get", side_effect=requests.RequestException)
def test_offline_template_used_on_backend_error(_mock_get, client):
    resp = client.get("/?year=2025&seasonType=2&week=1")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Offline" in body
    assert "No Data" in body


def test_season_type_name():
    """Test the season_type_name function."""
    from ..app import season_type_name

    assert season_type_name(1) == "Preseason"
    assert season_type_name(2) == "Regular Season"
    assert season_type_name(3) == "Postseason"
    assert season_type_name(999) == "Unknown"


def test_season_type_name_edge_cases():
    """Test season_type_name with edge cases."""
    from ..app import season_type_name

    # Test with None
    assert season_type_name(None) == "Unknown"

    # Test with negative numbers
    assert season_type_name(-1) == "Unknown"

    # Test with zero
    assert season_type_name(0) == "Unknown"


if __name__ == "__main__":
    pytest.main()
