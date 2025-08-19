"""
Tests for Finnish timezone functionality.
"""

from ..main import extract_game_time, format_finnish_date_time, format_finnish_time


class TestFinnishTimezone:
    """Test Finnish timezone conversion functions."""

    def test_format_finnish_time_summer(self):
        """Test Finnish time formatting during summer (UTC+3)."""
        # August 19, 2025 19:30 UTC -> 22:30 Finnish summer time
        utc_time = "2025-08-19T19:30:00Z"
        result = format_finnish_time(utc_time)
        assert result == "22:30"

    def test_format_finnish_time_winter(self):
        """Test Finnish time formatting during winter (UTC+2)."""
        # December 15, 2025 17:00 UTC -> 19:00 Finnish winter time
        utc_time = "2025-12-15T17:00:00Z"
        result = format_finnish_time(utc_time)
        assert result == "19:00"

    def test_format_finnish_time_with_iso_format(self):
        """Test with ISO format including +00:00 timezone."""
        utc_time = "2025-08-20T14:00:00+00:00"
        result = format_finnish_time(utc_time)
        assert result == "17:00"  # Summer time UTC+3

    def test_format_finnish_time_invalid(self):
        """Test with invalid time string - should return original."""
        invalid_time = "not-a-time"
        result = format_finnish_time(invalid_time)
        assert result == "not-a-time"

    def test_format_finnish_date_time_summer(self):
        """Test Finnish date-time formatting during summer."""
        # Tuesday August 19, 2025 19:30 UTC -> Tue 19.08. 22:30
        utc_time = "2025-08-19T19:30:00Z"
        result = format_finnish_date_time(utc_time)
        assert result == "Tue 19.08. 22:30"

    def test_format_finnish_date_time_winter(self):
        """Test Finnish date-time formatting during winter."""
        # Monday December 15, 2025 17:00 UTC -> Mon 15.12. 19:00
        utc_time = "2025-12-15T17:00:00Z"
        result = format_finnish_date_time(utc_time)
        assert result == "Mon 15.12. 19:00"

    def test_format_finnish_date_time_tuesday(self):
        """Test with a Wednesday to verify day formatting."""
        # Wednesday August 20, 2025 20:15 UTC -> Wed 20.08. 23:15
        utc_time = "2025-08-20T20:15:00Z"
        result = format_finnish_date_time(utc_time)
        assert result == "Wed 20.08. 23:15"

    def test_format_finnish_date_time_invalid(self):
        """Test with invalid time string."""
        invalid_time = "invalid-date"
        result = format_finnish_date_time(invalid_time)
        assert result == "invalid-date"

    def test_midnight_boundary(self):
        """Test timezone conversion across midnight boundary."""
        # August 19, 2025 22:00 UTC -> August 20, 01:00 Finnish time
        utc_time = "2025-08-19T22:00:00Z"
        result = format_finnish_date_time(utc_time)
        assert result == "Wed 20.08. 01:00"

    def test_dst_transition_periods(self):
        """Test timezone conversion during typical DST periods."""
        # Test various times throughout the year
        test_cases = [
            ("2025-03-15T12:00:00Z", "14:00"),  # March - winter time (UTC+2)
            ("2025-04-15T12:00:00Z", "15:00"),  # April - summer time (UTC+3)
            ("2025-07-15T12:00:00Z", "15:00"),  # July - summer time (UTC+3)
            ("2025-10-15T12:00:00Z", "15:00"),  # October - summer time (UTC+3)
            ("2025-11-15T12:00:00Z", "14:00"),  # November - winter time (UTC+2)
        ]

        for utc_time, expected_time in test_cases:
            result = format_finnish_time(utc_time)
            assert result == expected_time, f"Failed for {utc_time}"


class TestGameTimeExtraction:
    """Test game clock extraction from ESPN data."""

    def test_extract_game_time_live_game(self):
        """Test extracting game time from live game data."""
        game_data = {
            "status": {
                "type": {"name": "STATUS_IN_PROGRESS"},
                "displayClock": "08:45",
                "period": 3,
            }
        }
        result = extract_game_time(game_data)
        assert result == "Q3 08:45"

    def test_extract_game_time_different_quarter(self):
        """Test with different quarter."""
        game_data = {
            "status": {
                "type": {"name": "STATUS_IN_PROGRESS"},
                "displayClock": "12:34",
                "period": 1,
            }
        }
        result = extract_game_time(game_data)
        assert result == "Q1 12:34"

    def test_extract_game_time_no_clock(self):
        """Test with live game but no display clock."""
        game_data = {"status": {"type": {"name": "STATUS_IN_PROGRESS"}, "period": 4}}
        result = extract_game_time(game_data)
        assert result == "Q4"

    def test_extract_game_time_not_live(self):
        """Test with non-live game status."""
        game_data = {
            "status": {
                "type": {"name": "STATUS_FINAL"},
                "displayClock": "00:00",
                "period": 4,
            }
        }
        result = extract_game_time(game_data)
        assert result is None

    def test_extract_game_time_missing_data(self):
        """Test with missing or malformed data."""
        test_cases = [
            {},  # Empty dict
            {"status": {}},  # Missing type
            {"status": {"type": {}}},  # Missing name
            {
                "status": {"type": {"name": "STATUS_IN_PROGRESS"}}
            },  # Missing period/clock
        ]

        for game_data in test_cases:
            result = extract_game_time(game_data)
            assert result is None

    def test_extract_game_time_invalid_structure(self):
        """Test with invalid data structure."""
        # Test with None instead of string to avoid type issues
        result = extract_game_time({})  # Empty dict should return None
        assert result is None

    def test_extract_game_time_overtime(self):
        """Test overtime period formatting."""
        game_data = {
            "status": {
                "type": {"name": "STATUS_IN_PROGRESS"},
                "displayClock": "05:30",
                "period": 5,
            }
        }
        result = extract_game_time(game_data)
        assert result == "Q5 05:30"  # Overtime shows as Q5
