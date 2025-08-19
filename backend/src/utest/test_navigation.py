"""
Tests for season navigation functionality.
"""

from fastapi.testclient import TestClient

from ..main import app, get_season_navigation

client = TestClient(app)


class TestSeasonNavigation:
    """Test the season navigation logic."""

    def test_preseason_normal_navigation(self):
        """Test normal navigation within preseason."""
        # Week 2 -> next should go to week 3
        result = get_season_navigation(2025, 2, 1, "next")
        assert result == {"year": 2025, "week": 3, "seasonType": 1}

        # Week 3 -> prev should go to week 2
        result = get_season_navigation(2025, 3, 1, "prev")
        assert result == {"year": 2025, "week": 2, "seasonType": 1}

    def test_preseason_to_regular_season(self):
        """Test transition from preseason to regular season."""
        # Last week of preseason (week 4) -> next should go to regular season week 1
        result = get_season_navigation(2025, 4, 1, "next")
        assert result == {"year": 2025, "week": 1, "seasonType": 2}

    def test_regular_season_to_preseason(self):
        """Test transition from regular season back to preseason."""
        # First week of regular season -> prev should go to preseason week 4
        result = get_season_navigation(2025, 1, 2, "prev")
        assert result == {"year": 2025, "week": 4, "seasonType": 1}

    def test_regular_season_normal_navigation(self):
        """Test normal navigation within regular season."""
        # Week 10 -> next should go to week 11
        result = get_season_navigation(2025, 10, 2, "next")
        assert result == {"year": 2025, "week": 11, "seasonType": 2}

        # Week 10 -> prev should go to week 9
        result = get_season_navigation(2025, 10, 2, "prev")
        assert result == {"year": 2025, "week": 9, "seasonType": 2}

    def test_regular_season_to_postseason(self):
        """Test transition from regular season to postseason."""
        # Last week of regular season (week 18) -> next should go to postseason week 1
        result = get_season_navigation(2025, 18, 2, "next")
        assert result == {"year": 2025, "week": 1, "seasonType": 3}

    def test_postseason_to_regular_season(self):
        """Test transition from postseason back to regular season."""
        # First week of postseason -> prev should go to regular season week 18
        result = get_season_navigation(2025, 1, 3, "prev")
        assert result == {"year": 2025, "week": 18, "seasonType": 2}

    def test_postseason_normal_navigation(self):
        """Test normal navigation within postseason."""
        # Week 2 -> next should go to week 3
        result = get_season_navigation(2025, 2, 3, "next")
        assert result == {"year": 2025, "week": 3, "seasonType": 3}

        # Week 3 -> prev should go to week 2
        result = get_season_navigation(2025, 3, 3, "prev")
        assert result == {"year": 2025, "week": 2, "seasonType": 3}

    def test_postseason_to_next_year(self):
        """Test transition from postseason to next year preseason."""
        # Last week of postseason (week 4) -> next should go to next year preseason week 1
        result = get_season_navigation(2025, 4, 3, "next")
        assert result == {"year": 2026, "week": 1, "seasonType": 1}

    def test_preseason_to_previous_year(self):
        """Test transition from preseason to previous year postseason."""
        # First week of preseason -> prev should go to previous year postseason week 4
        result = get_season_navigation(2025, 1, 1, "prev")
        assert result == {"year": 2024, "week": 4, "seasonType": 3}

    def test_boundary_weeks(self):
        """Test all boundary conditions."""
        test_cases = [
            # (year, week, season_type, direction) -> expected
            (
                (2025, 1, 1, "prev"),
                {"year": 2024, "week": 4, "seasonType": 3},
            ),  # First preseason -> prev year
            (
                (2025, 4, 1, "next"),
                {"year": 2025, "week": 1, "seasonType": 2},
            ),  # Last preseason -> regular
            (
                (2025, 1, 2, "prev"),
                {"year": 2025, "week": 4, "seasonType": 1},
            ),  # First regular -> preseason
            (
                (2025, 18, 2, "next"),
                {"year": 2025, "week": 1, "seasonType": 3},
            ),  # Last regular -> postseason
            (
                (2025, 1, 3, "prev"),
                {"year": 2025, "week": 18, "seasonType": 2},
            ),  # First postseason -> regular
            (
                (2025, 4, 3, "next"),
                {"year": 2026, "week": 1, "seasonType": 1},
            ),  # Last postseason -> next year
        ]

        for (year, week, season_type, direction), expected in test_cases:
            result = get_season_navigation(year, week, season_type, direction)
            assert result == expected, (
                f"Failed for {year}-{week}-{season_type}-{direction}"
            )

    def test_invalid_season_type(self):
        """Test with invalid season type - should fallback to regular season rules."""
        # Invalid season type should use regular season limits (1-18) and increment week
        result = get_season_navigation(2025, 5, 99, "next")
        assert result == {"year": 2025, "week": 6, "seasonType": 99}

    def test_invalid_direction(self):
        """Test with invalid direction - should fallback gracefully."""
        result = get_season_navigation(2025, 5, 2, "invalid")
        assert result == {"year": 2025, "week": 5, "seasonType": 2}


class TestNavigationEndpoint:
    """Test the navigation API endpoint."""

    def test_navigation_endpoint_next(self):
        """Test navigation endpoint for next week."""
        response = client.get(
            "/games/weekly/navigation",
            params={"year": 2025, "week": 4, "seasonType": 1, "direction": "next"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data == {"year": 2025, "week": 1, "seasonType": 2}

    def test_navigation_endpoint_prev(self):
        """Test navigation endpoint for previous week."""
        response = client.get(
            "/games/weekly/navigation",
            params={"year": 2025, "week": 1, "seasonType": 2, "direction": "prev"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data == {"year": 2025, "week": 4, "seasonType": 1}

    def test_navigation_endpoint_invalid_direction(self):
        """Test navigation endpoint with invalid direction."""
        response = client.get(
            "/games/weekly/navigation",
            params={"year": 2025, "week": 1, "seasonType": 2, "direction": "invalid"},
        )
        assert response.status_code == 400
        assert "Direction must be 'next' or 'prev'" in response.json()["detail"]

    def test_navigation_endpoint_missing_params(self):
        """Test navigation endpoint with missing required parameters."""
        response = client.get("/games/weekly/navigation")
        assert response.status_code == 422  # Validation error

    def test_navigation_endpoint_year_transitions(self):
        """Test navigation endpoint across year boundaries."""
        # Test going from 2025 postseason to 2026 preseason
        response = client.get(
            "/games/weekly/navigation",
            params={"year": 2025, "week": 4, "seasonType": 3, "direction": "next"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data == {"year": 2026, "week": 1, "seasonType": 1}

        # Test going from 2025 preseason to 2024 postseason
        response = client.get(
            "/games/weekly/navigation",
            params={"year": 2025, "week": 1, "seasonType": 1, "direction": "prev"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data == {"year": 2024, "week": 4, "seasonType": 3}


class TestSeasonLimits:
    """Test season limit constants and edge cases."""

    def test_preseason_limits(self):
        """Test preseason week limits (1-4)."""
        # Should stay within bounds
        result = get_season_navigation(2025, 2, 1, "next")
        assert result["week"] == 3 and result["seasonType"] == 1

        result = get_season_navigation(2025, 3, 1, "prev")
        assert result["week"] == 2 and result["seasonType"] == 1

    def test_regular_season_limits(self):
        """Test regular season week limits (1-18)."""
        # Test middle weeks
        result = get_season_navigation(2025, 10, 2, "next")
        assert result["week"] == 11 and result["seasonType"] == 2

        # Test near boundaries
        result = get_season_navigation(2025, 17, 2, "next")
        assert result["week"] == 18 and result["seasonType"] == 2

    def test_postseason_limits(self):
        """Test postseason week limits (1-4)."""
        # Should stay within bounds
        result = get_season_navigation(2025, 2, 3, "next")
        assert result["week"] == 3 and result["seasonType"] == 3

        result = get_season_navigation(2025, 3, 3, "prev")
        assert result["week"] == 2 and result["seasonType"] == 3
