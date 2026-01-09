"""Tests for playoff bracket functionality and mock data infrastructure."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ..main import _detect_fixture_name, _load_fixture, app

# Reusable patch decorator for mock mode tests
mock_espn = patch("src.main.MOCK_ESPN", True)


class TestFixtureLoading:
    """Tests for fixture loading mechanism."""

    def test_load_fixture_regular_season(self):
        """Test loading regular season fixture."""
        fixture = _load_fixture("regular_season")
        assert isinstance(fixture, dict)
        assert "games" in fixture
        assert "season" in fixture
        assert fixture["season"]["type"] == 2

    def test_load_fixture_postseason_wildcard(self):
        """Test loading postseason wildcard fixture."""
        fixture = _load_fixture("postseason_wildcard")
        assert isinstance(fixture, dict)
        assert "games" in fixture
        assert fixture["season"]["type"] == 3
        assert fixture["week"]["number"] == 1

    def test_load_fixture_standings(self):
        """Test loading standings fixture."""
        standings = _load_fixture("standings")
        assert isinstance(standings, list)
        assert len(standings) == 32  # All NFL teams
        assert all("team" in s and "wins" in s and "losses" in s for s in standings)

    def test_load_fixture_playoff_seeds(self):
        """Test loading playoff seeds fixture."""
        bracket = _load_fixture("playoff_seeds")
        assert isinstance(bracket, dict)
        assert "afc_seeds" in bracket
        assert "nfc_seeds" in bracket
        assert "games" in bracket
        assert len(bracket["afc_seeds"]) == 7
        assert len(bracket["nfc_seeds"]) == 7

    def test_load_nonexistent_fixture_raises(self):
        """Test that loading nonexistent fixture raises HTTPException."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _load_fixture("nonexistent_fixture")
        assert exc_info.value.status_code == 404  # type: ignore[union-attr]


class TestFixtureDetection:
    """Tests for fixture detection logic."""

    def test_detect_regular_season(self):
        """Test fixture detection for regular season."""
        assert _detect_fixture_name(2024, 15, 2) == "regular_season"
        assert _detect_fixture_name(2024, 1, 2) == "regular_season"
        assert _detect_fixture_name(2024, 18, 2) == "regular_season"

    def test_detect_postseason_wildcard(self):
        """Test fixture detection for wild card round."""
        assert _detect_fixture_name(2024, 1, 3) == "postseason_wildcard"

    def test_detect_postseason_divisional(self):
        """Test fixture detection for divisional round."""
        assert _detect_fixture_name(2024, 2, 3) == "postseason_divisional"

    def test_detect_postseason_conference(self):
        """Test fixture detection for conference championships."""
        assert _detect_fixture_name(2024, 3, 3) == "postseason_conference"

    def test_detect_postseason_superbowl(self):
        """Test fixture detection for Super Bowl."""
        assert _detect_fixture_name(2024, 4, 3) == "postseason_superbowl"

    def test_detect_preseason_defaults_to_regular(self):
        """Test fixture detection defaults to regular season for preseason."""
        assert _detect_fixture_name(2024, 1, 1) == "regular_season"


@mock_espn
class TestPlayoffBracketEndpoint:
    """Tests for the /playoffs/bracket endpoint."""

    def test_bracket_endpoint_mock_mode(self):
        """Test bracket endpoint returns data in mock mode."""
        client = TestClient(app)
        response = client.get("/playoffs/bracket")
        assert response.status_code == 200
        data = response.json()
        assert "season_year" in data
        assert "afc_seeds" in data
        assert "nfc_seeds" in data
        assert "games" in data

    def test_bracket_seeds_structure(self):
        """Test bracket seeds have correct structure."""
        client = TestClient(app)
        response = client.get("/playoffs/bracket")
        data = response.json()

        for seed in data["afc_seeds"]:
            assert "seed" in seed
            assert "team" in seed
            assert "abbreviation" in seed
            assert "eliminated" in seed

    def test_bracket_games_structure(self):
        """Test bracket games have correct structure."""
        client = TestClient(app)
        response = client.get("/playoffs/bracket")
        data = response.json()

        for game in data["games"]:
            assert "round" in game
            assert "conference" in game
            assert "home_team" in game
            assert "away_team" in game
            assert "status" in game


@mock_espn
class TestMockModeGamesEndpoint:
    """Tests for games endpoint in mock mode."""

    def test_weekly_games_mock_mode(self):
        """Test weekly games endpoint returns fixture data in mock mode."""
        client = TestClient(app)
        response = client.get("/games/weekly")
        assert response.status_code == 200
        games = response.json()
        assert isinstance(games, list)
        assert len(games) > 0

    def test_weekly_games_fixture_override(self):
        """Test weekly games with explicit fixture parameter."""
        client = TestClient(app)
        response = client.get("/games/weekly?fixture=postseason_wildcard")
        assert response.status_code == 200
        games = response.json()
        assert isinstance(games, list)
        # Wildcard has 6 games
        assert len(games) == 6

    def test_weekly_context_mock_mode(self):
        """Test context endpoint returns fixture context in mock mode."""
        client = TestClient(app)
        response = client.get("/games/weekly/context")
        assert response.status_code == 200
        ctx = response.json()
        assert "year" in ctx
        assert "week" in ctx
        assert "seasonType" in ctx


@mock_espn
class TestMockModeStandingsEndpoint:
    """Tests for standings endpoint in mock mode."""

    def test_live_standings_mock_mode(self):
        """Test live standings endpoint returns fixture data in mock mode."""
        client = TestClient(app)
        response = client.get("/standings/live")
        assert response.status_code == 200
        standings = response.json()
        assert isinstance(standings, list)
        assert len(standings) == 32  # All NFL teams


class TestFixtureFilesExist:
    """Verify all required fixture files exist."""

    @pytest.fixture
    def fixtures_path(self):
        """Return path to fixtures directory."""
        return Path(__file__).parent.parent / "fixtures"

    def test_regular_season_exists(self, fixtures_path):
        """Test regular_season.json exists."""
        assert (fixtures_path / "regular_season.json").exists()

    def test_postseason_wildcard_exists(self, fixtures_path):
        """Test postseason_wildcard.json exists."""
        assert (fixtures_path / "postseason_wildcard.json").exists()

    def test_postseason_divisional_exists(self, fixtures_path):
        """Test postseason_divisional.json exists."""
        assert (fixtures_path / "postseason_divisional.json").exists()

    def test_postseason_conference_exists(self, fixtures_path):
        """Test postseason_conference.json exists."""
        assert (fixtures_path / "postseason_conference.json").exists()

    def test_postseason_superbowl_exists(self, fixtures_path):
        """Test postseason_superbowl.json exists."""
        assert (fixtures_path / "postseason_superbowl.json").exists()

    def test_standings_exists(self, fixtures_path):
        """Test standings.json exists."""
        assert (fixtures_path / "standings.json").exists()

    def test_playoff_seeds_exists(self, fixtures_path):
        """Test playoff_seeds.json exists."""
        assert (fixtures_path / "playoff_seeds.json").exists()

    def test_all_fixtures_are_valid_json(self, fixtures_path):
        """Test all fixtures are valid JSON."""
        for fixture_file in fixtures_path.glob("*.json"):
            with open(fixture_file) as f:
                data = json.load(f)
                assert data is not None
