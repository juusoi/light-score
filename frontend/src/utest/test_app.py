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
    assert (
        b'<link rel="icon" type="image/svg+xml" href="/static/favicon.svg" />'
        in response.data
    )


def test_health_route(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_static_favicon_is_served(client):
    response = client.get("/static/favicon.svg")
    assert response.status_code == 200
    assert "image/svg+xml" in response.content_type


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
def test_bracket_fallback_to_standings_on_error(mock_get, client):
    """Test that standings are shown when bracket fetch fails in postseason."""
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
    nav_json = {"year": 2024, "week": 2, "seasonType": 3}

    def side_effect(url, **kwargs):
        if "playoffs/bracket" in url:
            # Simulate network error or invalid response
            r = MagicMock(ok=False)
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
    # Bracket panel should NOT be shown (bracket fetch failed)
    assert "Playoff Bracket" not in text
    # Standings should be shown as fallback
    assert "Standings" in text
    assert "Kansas City Chiefs" in text


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


def test_get_team_logo_resolver():
    """Test get_team_logo function resolves team logos case-insensitively and provides fallback."""
    from ..app import get_team_logo

    # Verify known teams resolve to a color tile with their abbreviation
    cowboys_svg = get_team_logo("Dallas Cowboys")
    assert "ttx-logo" in cowboys_svg
    assert ">DAL<" in cowboys_svg
    assert "#002244" in cowboys_svg

    dolphins_svg = get_team_logo("Miami Dolphins")
    assert "ttx-logo" in dolphins_svg
    assert ">MIA<" in dolphins_svg
    assert "#008e97" in dolphins_svg

    # Verify fallback for unknown team: neutral tile with derived initials
    unknown_svg = get_team_logo("Unknown Team")
    assert "ttx-logo" in unknown_svg
    assert ">UT<" in unknown_svg
    assert "#555555" in unknown_svg

    # None handling
    assert get_team_logo(None) == ""


def test_badge_text_color_contrast():
    """Badge text color flips to stay legible against light vs dark tiles."""
    from ..app import _badge_text_color

    # Light backgrounds get dark text (e.g. Steelers gold).
    assert _badge_text_color("#ffb612") == "#101820"
    assert _badge_text_color("#ffffff") == "#101820"
    # Dark backgrounds get white text (e.g. Cowboys navy).
    assert _badge_text_color("#002244") == "#ffffff"
    assert _badge_text_color("#000000") == "#ffffff"


def test_all_known_teams_resolve_uniquely():
    """Every team in the table resolves to its own badge; abbreviations are unique."""
    from ..app import TEAM_BADGES, get_team_logo

    for key, (abbr, color) in TEAM_BADGES.items():
        # A realistic full name containing the nickname must resolve to this team,
        # i.e. no earlier substring match shadows it.
        svg = get_team_logo(f"Some City {key.title()}")
        assert "ttx-logo" in svg
        assert f">{abbr}<" in svg
        assert color in svg

    abbrs = [abbr for abbr, _ in TEAM_BADGES.values()]
    assert len(set(abbrs)) == len(abbrs), "duplicate team abbreviations"


def test_fallback_abbr_derivation():
    """Unknown teams get a neutral tile with initials derived from the name."""
    from ..app import get_team_logo

    multi = get_team_logo("Birmingham Iron Squad")
    assert ">BIS<" in multi
    assert "#555555" in multi

    single = get_team_logo("Spartans")
    assert ">SPA<" in single
    assert "#555555" in single


@patch("requests.get")
def test_no_scores_shows_only_upcoming_games(mock_get, client):
    """Test /no-scores shows only this week's upcoming games with no spoilers."""
    weekly = [
        {
            "team_a": "Kansas City Chiefs",
            "team_b": "Las Vegas Raiders",
            "status": "final",
            "start_time": "2026-11-26T17:30:00Z",
            "start_time_finnish": None,
            "start_date_time_finnish": None,
            "game_time": None,
            "score_a": 27,
            "score_b": 14,
        },
        {
            "team_a": "Green Bay Packers",
            "team_b": "Seattle Seahawks",
            "status": "live",
            "start_time": "2026-11-27T18:00:00Z",
            "start_time_finnish": None,
            "start_date_time_finnish": None,
            "game_time": "Q3 7:42",
            "score_a": 21,
            "score_b": 17,
        },
        {
            "team_a": "San Francisco 49ers",
            "team_b": "Los Angeles Rams",
            "status": "upcoming",
            "start_time": "2026-11-29T18:00:00Z",
            "start_time_finnish": "20:00",
            "start_date_time_finnish": "Sun 29.11. 20:00",
            "game_time": None,
            "score_a": None,
            "score_b": None,
        },
        {
            "team_a": "Dallas Cowboys",
            "team_b": "Carolina Panthers",
            "status": "upcoming",
            "start_time": "2026-11-30T01:20:00Z",
            "start_time_finnish": "03:20",
            "start_date_time_finnish": "Mon 30.11. 03:20",
            "game_time": None,
            "score_a": None,
            "score_b": None,
        },
    ]
    ctx_json = {"year": 2026, "week": 13, "seasonType": 2}
    requested_urls: list[str] = []

    def side_effect(url, **kwargs):
        requested_urls.append(url)
        if url.endswith("/games/weekly"):
            r = MagicMock(ok=True)
            r.json.return_value = weekly
            return r
        if url.endswith("/games/weekly/context"):
            r = MagicMock(ok=True)
            r.json.return_value = ctx_json
            return r
        raise AssertionError(f"Unexpected backend call: {url}")

    mock_get.side_effect = side_effect
    resp = client.get("/no-scores")
    assert resp.status_code == 200
    text = resp.data.decode("utf-8")

    # Header and upcoming panel rendered
    assert "Light Score" in text
    assert "Regular Season" in text
    assert "2026" in text
    assert "Week 13" in text
    assert "Upcoming Games" in text

    # Upcoming games and kickoff times shown
    assert "San Francisco 49ers" in text
    assert "Los Angeles Rams" in text
    assert "Sun 29.11. 20:00" in text
    assert "Dallas Cowboys" in text
    assert "Carolina Panthers" in text
    assert "Mon 30.11. 03:20" in text

    # Final and live games, scores, clocks, and spoiler panels excluded
    assert "Kansas City Chiefs" not in text
    assert "Las Vegas Raiders" not in text
    assert "Green Bay Packers" not in text
    assert "Seattle Seahawks" not in text
    assert "Q3 7:42" not in text
    assert "27" not in text
    assert "ttx-score" not in text
    assert "ttx-status-live" not in text
    assert "ttx-status-final" not in text
    assert "<h2>Live</h2>" not in text
    assert "<h2>Standings</h2>" not in text
    assert "Playoff Bracket" not in text
    assert "Prev" not in text
    assert "Next" not in text
    assert 'href="/"' not in text

    # Only games/weekly and games/weekly/context called
    assert len(requested_urls) == 2
    assert any(u.endswith("/games/weekly") for u in requested_urls)
    assert any(u.endswith("/games/weekly/context") for u in requested_urls)


@patch("requests.get")
def test_no_scores_empty_when_no_upcoming_games(mock_get, client):
    """Test /no-scores renders empty state when only final/live games exist."""
    weekly = [
        {
            "team_a": "Buffalo Bills",
            "team_b": "Detroit Lions",
            "status": "final",
            "start_time": "2026-11-26T18:00:00Z",
            "start_time_finnish": None,
            "start_date_time_finnish": None,
            "game_time": None,
            "score_a": 42,
            "score_b": 35,
        },
        {
            "team_a": "Philadelphia Eagles",
            "team_b": "Pittsburgh Steelers",
            "status": "live",
            "start_time": "2026-11-27T18:00:00Z",
            "start_time_finnish": None,
            "start_date_time_finnish": None,
            "game_time": "Q2 2:05",
            "score_a": 14,
            "score_b": 10,
        },
    ]
    ctx_json = {"year": 2026, "week": 13, "seasonType": 2}

    def side_effect(url, **kwargs):
        r = MagicMock(ok=True)
        r.json.return_value = ctx_json if url.endswith("/context") else weekly
        return r

    mock_get.side_effect = side_effect
    resp = client.get("/no-scores")
    assert resp.status_code == 200
    text = resp.data.decode("utf-8")

    assert "No upcoming games" in text
    assert "Buffalo Bills" not in text
    assert "Philadelphia Eagles" not in text
    assert "42" not in text
    assert "Q2 2:05" not in text


@patch("requests.get")
def test_no_scores_ignores_query_params(mock_get, client):
    """Test /no-scores always fetches current week and ignores query params."""
    seen_params: list[dict] = []

    def side_effect(url, **kwargs):
        seen_params.append(kwargs.get("params", {}))
        r = MagicMock(ok=True)
        if url.endswith("/context"):
            r.json.return_value = {"year": 2026, "week": 13, "seasonType": 2}
        else:
            r.json.return_value = []
        return r

    mock_get.side_effect = side_effect
    resp = client.get("/no-scores?year=2024&week=5&seasonType=3")
    assert resp.status_code == 200
    assert seen_params == [{}, {}]
    text = resp.data.decode("utf-8")
    assert "Week 13" in text
    assert "Regular Season" in text


@patch("requests.get", side_effect=requests.RequestException("backend down"))
def test_no_scores_offline_fallback_on_backend_error(_mock_get, client):
    """Test /no-scores renders offline fallback page on network failure."""
    resp = client.get("/no-scores")
    assert resp.status_code == 200
    text = resp.data.decode("utf-8")
    assert "Offline" in text
    assert "No Data" in text


@patch("requests.get")
def test_no_scores_handles_error_or_malformed_backend_payload(mock_get, client):
    """Test /no-scores degrades safely on non-OK or malformed backend payloads."""

    def side_effect(url, **kwargs):
        if url.endswith("/games/weekly"):
            r = MagicMock(ok=False, status_code=502)
            r.json.return_value = {"detail": "ESPN API error"}
            return r
        r = MagicMock(ok=False, status_code=504)
        r.json.return_value = {"detail": "timeout"}
        return r

    mock_get.side_effect = side_effect
    resp = client.get("/no-scores")
    assert resp.status_code == 200
    text = resp.data.decode("utf-8")
    assert "Upcoming Games" in text
    assert "No upcoming games" in text
    assert "Regular Season" in text
    assert "Week 1" in text


@patch("requests.get")
def test_no_scores_filters_malformed_game_entries(mock_get, client):
    """Test /no-scores ignores non-dict or non-string game entries without crashing."""
    weekly = [
        "not-a-dict",
        {"team_a": 123, "team_b": "Valid Team", "status": "upcoming"},
        {"team_a": None, "team_b": "Valid Team", "status": "upcoming"},
        {"team_a": "Missing Status", "team_b": "Other"},
        {
            "team_a": "A&B <Club>",
            "team_b": "Chicago Bears",
            "status": "upcoming",
            "start_date_time_finnish": "Sun 29.11. 20:00",
        },
    ]

    def side_effect(url, **kwargs):
        r = MagicMock(ok=True)
        if url.endswith("/context"):
            r.json.return_value = {"unexpected": "shape"}
        else:
            r.json.return_value = weekly
        return r

    mock_get.side_effect = side_effect
    resp = client.get("/no-scores")
    assert resp.status_code == 200
    text = resp.data.decode("utf-8")
    assert "Chicago Bears" in text
    assert "A&amp;B &lt;Club&gt;" in text
    assert ">A&lt;<" in text
    assert "Regular Season" in text
    assert "Week 1" in text


@patch("requests.get")
def test_no_scores_kickoff_time_fallbacks(mock_get, client):
    """Test kickoff time fallback order: date_time -> time -> iso -> scheduled."""
    weekly = [
        {
            "team_a": "Miami Dolphins",
            "team_b": "New York Jets",
            "status": "upcoming",
            "start_time": "2026-11-29T18:00:00Z",
            "start_time_finnish": "20:00",
            "start_date_time_finnish": None,
        },
        {
            "team_a": "Chicago Bears",
            "team_b": "Minnesota Vikings",
            "status": "upcoming",
            "start_time": "2026-11-29T21:25:00Z",
            "start_time_finnish": None,
            "start_date_time_finnish": None,
        },
        {
            "team_a": "Atlanta Falcons",
            "team_b": "New Orleans Saints",
            "status": "upcoming",
            "start_time": None,
            "start_time_finnish": None,
            "start_date_time_finnish": None,
        },
    ]

    def side_effect(url, **kwargs):
        r = MagicMock(ok=True)
        if url.endswith("/context"):
            r.json.return_value = {"year": 2026, "week": 13, "seasonType": 2}
        else:
            r.json.return_value = weekly
        return r

    mock_get.side_effect = side_effect
    resp = client.get("/no-scores")
    assert resp.status_code == 200
    text = resp.data.decode("utf-8")
    assert "20:00" in text
    assert "2026-11-29T21:25:00Z" in text
    assert "scheduled" in text


@patch("requests.get")
def test_home_does_not_link_to_no_scores(mock_get, client):
    """Test landing page does not link to /no-scores yet."""

    def side_effect(url, **kwargs):
        r = MagicMock(ok=True)
        if url.endswith("/context"):
            r.json.return_value = {"year": 2026, "week": 13, "seasonType": 2}
        elif "/navigation" in url:
            r.json.return_value = {"year": 2026, "week": 12, "seasonType": 2}
        else:
            r.json.return_value = []
        return r

    mock_get.side_effect = side_effect
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"/no-scores" not in resp.data


if __name__ == "__main__":
    pytest.main()
