from unittest.mock import MagicMock, patch

import pytest
from flask_testing import TestCase

from ..app import app


class MyTest(TestCase):
    def create_app(self):
        app.config["TESTING"] = True
        return app

    def test_home_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        # Should render the teletext layout (offline variant when backend not reachable in tests)
        self.assertIn(b"Light Score", response.data)

    @patch("requests.get")
    def test_home_route_with_navigation_params(self, mock_get):
        """Test home route with navigation parameters."""
        # Mock the backend responses
        mock_weekly_response = MagicMock()
        mock_weekly_response.ok = True
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

        mock_context_response = MagicMock()
        mock_context_response.ok = True
        mock_context_response.json.return_value = {
            "year": 2025,
            "week": 3,
            "seasonType": 1,
        }

        mock_standings_response = MagicMock()
        mock_standings_response.ok = True
        mock_standings_response.json.return_value = [
            {"team": "Team 1", "wins": 2, "losses": 0, "division": "AFC East"}
        ]

        mock_nav_response = MagicMock()
        mock_nav_response.ok = True
        mock_nav_response.json.return_value = {"year": 2025, "week": 2, "seasonType": 1}

        # Configure mock to return different responses for different URLs
        def mock_get_side_effect(url, **kwargs):
            if "weekly" in url and "context" not in url:
                return mock_weekly_response
            elif "context" in url:
                return mock_context_response
            elif "standings/live" in url:
                return mock_standings_response
            elif "navigation" in url:
                return mock_nav_response
            return MagicMock(ok=False)

        mock_get.side_effect = mock_get_side_effect

        # Test with specific week parameters
        response = self.client.get("/?year=2025&seasonType=1&week=3")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Light Score", response.data)
        # Should include navigation links in the response
        self.assertIn(b"Prev week", response.data)
        self.assertIn(b"Next week", response.data)

    @patch("requests.get")
    def test_navigation_parameters_in_response(self, mock_get):
        """Test that navigation parameters are properly included in the response."""
        # Mock the backend responses
        mock_weekly_response = MagicMock()
        mock_weekly_response.ok = True
        mock_weekly_response.json.return_value = []

        mock_context_response = MagicMock()
        mock_context_response.ok = True
        mock_context_response.json.return_value = {
            "year": 2025,
            "week": 1,
            "seasonType": 2,
        }

        mock_standings_response = MagicMock()
        mock_standings_response.ok = True
        mock_standings_response.json.return_value = []

        mock_nav_response = MagicMock()
        mock_nav_response.ok = True
        mock_nav_response.json.return_value = {"year": 2025, "week": 2, "seasonType": 2}

        # Configure mock to return different responses for different URLs
        def mock_get_side_effect(url, **kwargs):
            if "weekly" in url and "context" not in url:
                return mock_weekly_response
            elif "context" in url:
                return mock_context_response
            elif "standings/live" in url:
                return mock_standings_response
            elif "navigation" in url:
                return mock_nav_response
            return MagicMock(ok=False)

        mock_get.side_effect = mock_get_side_effect

        response = self.client.get("/?year=2025&seasonType=2&week=1")
        self.assertEqual(response.status_code, 200)

        # The response should contain navigation links with mocked backend
        response_text = response.data.decode("utf-8")
        self.assertIn("Prev week", response_text)
        self.assertIn("Next week", response_text)


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
