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
        {
            "team": "Team 1",
            "wins": 2,
            "losses": 0,
            "ties": 1,
            "division": "AFC East",
        }
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
    text = body.decode("utf-8")
    assert 'class="ttx-record"' in text
    assert '<span class="ttx-record-ties">1</span>' in text


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
    assert "Games" in text
    # Teams now rendered on separate lines without 'vs'
    assert "A" in text and "B" in text
    assert "21" in text and "17" in text
    # Winner highlighting should apply (team A wins 21-17)
    assert "ttx-winner" in text
    assert "C" in text and "D" in text
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


@patch("requests.get")
def test_bracket_panel_shown_in_postseason(mock_get, client):
    """Test that bracket panel appears when seasonType=3."""
    weekly = [
        {
            "team_a": "Pittsburgh Steelers",
            "team_b": "Buffalo Bills",
            "status": "final",
            "start_time": "2025-01-11T18:00:00Z",
            "start_time_finnish": None,
            "start_date_time_finnish": None,
            "game_time": None,
            "score_a": 17,
            "score_b": 31,
        },
    ]
    ctx_json = {"year": 2024, "week": 1, "seasonType": 3}
    standings_json = [
        {
            "team": "Kansas City Chiefs",
            "wins": 15,
            "losses": 2,
            "ties": 0,
            "division": "AFC West",
        }
    ]
    bracket_json = {
        "season_year": 2024,
        "afc_seeds": [
            {
                "seed": 1,
                "team": "Kansas City Chiefs",
                "abbreviation": "KC",
                "eliminated": False,
            },
            {
                "seed": 2,
                "team": "Buffalo Bills",
                "abbreviation": "BUF",
                "eliminated": False,
            },
        ],
        "nfc_seeds": [
            {
                "seed": 1,
                "team": "Detroit Lions",
                "abbreviation": "DET",
                "eliminated": True,
            },
            {
                "seed": 2,
                "team": "Philadelphia Eagles",
                "abbreviation": "PHI",
                "eliminated": False,
            },
        ],
        "games": [
            {
                "round": "Wild Card",
                "round_number": 1,
                "conference": "AFC",
                "home_team": "Buffalo Bills",
                "home_seed": 2,
                "home_score": 31,
                "away_team": "Pittsburgh Steelers",
                "away_seed": 6,
                "away_score": 17,
                "status": "final",
                "winner": "Buffalo Bills",
            }
        ],
    }
    nav_json = {"year": 2024, "week": 2, "seasonType": 3}

    def side_effect(url, **kwargs):
        if "playoffs/bracket" in url:
            r = MagicMock(ok=True)
            r.json.return_value = bracket_json
            return r
        elif "weekly" in url and "context" not in url:
            r = MagicMock(ok=True)
            r.json.return_value = weekly
            return r
        elif "context" in url:
            r = MagicMock(ok=True)
            r.json.return_value = ctx_json
            return r
        elif "standings/live" in url:
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
    resp = client.get("/?year=2024&seasonType=3&week=1")
    assert resp.status_code == 200
    text = resp.data.decode()
    # Bracket panel should be shown
    assert "Playoff Bracket" in text
    assert "AFC" in text
    assert "NFC" in text
    # Seeds should be displayed
    assert "(1)" in text
    assert "(2)" in text
    # Games should be shown
    assert "Wild Card" in text


@patch("requests.get")
def test_standings_panel_shown_in_regular_season(mock_get, client):
    """Test that standings panel appears when seasonType!=3."""
    weekly = []
    ctx_json = {"year": 2024, "week": 15, "seasonType": 2}
    standings_json = [
        {
            "team": "Kansas City Chiefs",
            "wins": 13,
            "losses": 2,
            "ties": 0,
            "division": "AFC West",
        }
    ]
    nav_json = {"year": 2024, "week": 14, "seasonType": 2}

    def side_effect(url, **kwargs):
        if "weekly" in url and "context" not in url:
            r = MagicMock(ok=True)
            r.json.return_value = weekly
            return r
        elif "context" in url:
            r = MagicMock(ok=True)
            r.json.return_value = ctx_json
            return r
        elif "standings/live" in url:
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
    resp = client.get("/?year=2024&seasonType=2&week=15")
    assert resp.status_code == 200
    text = resp.data.decode()
    # Regular standings panel should be shown
    assert "Standings" in text
    assert "AFC West" in text
    # Bracket panel should NOT be shown
    assert "Playoff Bracket" not in text


def test_render_bracket_line():
    """Test the bracket line rendering helper."""
    from ..app import render_bracket_line

    # Winner is team1
    result = render_bracket_line("Chiefs", 23, "Bills", 20, "Chiefs")
    assert "►Chiefs" in result
    assert " Bills" in result
    assert "23" in result
    assert "20" in result

    # Winner is team2
    result = render_bracket_line("Chiefs", 20, "Bills", 23, "Bills")
    assert " Chiefs" in result
    assert "►Bills" in result

    # No winner yet
    result = render_bracket_line("Chiefs", None, "Eagles", None, None)
    assert " Chiefs" in result
    assert " Eagles" in result
    assert "-" in result


@patch("requests.get")
def test_playoffs_route_loads(mock_get, client):
    """Test that /playoffs route loads successfully."""
    picture_json = {
        "season_year": 2024,
        "season_type": 2,
        "week": 15,
        "afc_teams": [
            {
                "team": "Kansas City Chiefs",
                "abbreviation": "KC",
                "conference": "AFC",
                "division": "AFC West",
                "wins": 15,
                "losses": 2,
                "ties": 0,
                "seed": 1,
                "status": "division_leader",
                "status_detail": "#1 seed (division leader)",
                "eliminated_round": None,
                "playoff_wins": 0,
                "playoff_losses": 0,
            }
        ],
        "nfc_teams": [
            {
                "team": "Detroit Lions",
                "abbreviation": "DET",
                "conference": "NFC",
                "division": "NFC North",
                "wins": 14,
                "losses": 3,
                "ties": 0,
                "seed": 1,
                "status": "division_leader",
                "status_detail": "#1 seed (division leader)",
                "eliminated_round": None,
                "playoff_wins": 0,
                "playoff_losses": 0,
            }
        ],
        "super_bowl_teams": [],
    }

    def side_effect(url, **kwargs):
        if "playoffs/picture" in url:
            r = MagicMock(ok=True)
            r.json.return_value = picture_json
            return r
        return MagicMock(ok=False)

    mock_get.side_effect = side_effect
    resp = client.get("/playoffs")
    assert resp.status_code == 200
    text = resp.data.decode()
    assert "Seedings" in text
    assert "AFC" in text
    assert "NFC" in text


@patch("requests.get")
def test_playoffs_route_regular_season(mock_get, client):
    """Test /playoffs route with regular season view."""
    picture_json = {
        "season_year": 2024,
        "season_type": 2,
        "week": 15,
        "afc_teams": [
            {
                "team": "Kansas City Chiefs",
                "abbreviation": "KC",
                "conference": "AFC",
                "division": "AFC West",
                "wins": 15,
                "losses": 2,
                "ties": 0,
                "seed": 1,
                "status": "division_leader",
                "status_detail": "#1 seed (division leader)",
                "eliminated_round": None,
                "playoff_wins": 0,
                "playoff_losses": 0,
            }
        ],
        "nfc_teams": [],
        "super_bowl_teams": [],
    }

    def side_effect(url, **kwargs):
        if "playoffs/picture" in url:
            r = MagicMock(ok=True)
            r.json.return_value = picture_json
            return r
        return MagicMock(ok=False)

    mock_get.side_effect = side_effect
    resp = client.get("/playoffs?seasonType=2")
    assert resp.status_code == 200
    text = resp.data.decode()
    assert "Playoff Seeds" in text
    assert "KC" in text


@patch("requests.get")
def test_playoffs_route_postseason(mock_get, client):
    """Test /playoffs route with postseason view."""
    picture_json = {
        "season_year": 2024,
        "season_type": 3,
        "week": 1,
        "afc_teams": [
            {
                "team": "Kansas City Chiefs",
                "abbreviation": "KC",
                "conference": "AFC",
                "division": "",
                "wins": 0,
                "losses": 0,
                "ties": 0,
                "seed": 1,
                "status": "super_bowl",
                "status_detail": "Super Bowl",
                "eliminated_round": None,
                "playoff_wins": 3,
                "playoff_losses": 0,
            }
        ],
        "nfc_teams": [
            {
                "team": "Philadelphia Eagles",
                "abbreviation": "PHI",
                "conference": "NFC",
                "division": "",
                "wins": 0,
                "losses": 0,
                "ties": 0,
                "seed": 2,
                "status": "super_bowl",
                "status_detail": "Super Bowl",
                "eliminated_round": None,
                "playoff_wins": 3,
                "playoff_losses": 0,
            }
        ],
        "super_bowl_teams": ["Kansas City Chiefs", "Philadelphia Eagles"],
    }

    def side_effect(url, **kwargs):
        if "playoffs/picture" in url:
            r = MagicMock(ok=True)
            r.json.return_value = picture_json
            return r
        return MagicMock(ok=False)

    mock_get.side_effect = side_effect
    resp = client.get("/playoffs?seasonType=3")
    assert resp.status_code == 200
    text = resp.data.decode()
    assert "Super Bowl" in text
    assert "KC" in text
    assert "PHI" in text


@patch("requests.get", side_effect=requests.RequestException)
def test_playoffs_route_handles_error(_mock_get, client):
    """Test /playoffs route handles network errors gracefully."""
    resp = client.get("/playoffs")
    assert resp.status_code == 200
    text = resp.data.decode()
    assert "Network error" in text


if __name__ == "__main__":
    pytest.main()
