import json
from unittest.mock import patch
from ..main import save_standings_cache
from ..standings_parser import ConferenceGroup, TeamStandingInfo


def test_save_standings_cache():
    team = TeamStandingInfo(
        name="Mock Team",
        abbreviation_name="MT",
        wins=10,
        losses=4,
        ties=1,
        win_percentage=0.700,
        points_for=400,
        points_against=300,
        streak=2,
        home_record=(5, 2),
        away_record=(5, 2),
        division_record=(4, 1),
        conference_record=(8, 2),
    )
    group = ConferenceGroup(name="AFC East")
    group.add_team(team)

    with (
        patch("pathlib.Path.write_text") as mock_write,
        patch("pathlib.Path.mkdir") as _mock_mkdir,
    ):
        save_standings_cache([group], [])

        # Verify write_text was called
        assert mock_write.called
        written_data = json.loads(mock_write.call_args[0][0])
        assert len(written_data) == 1
        assert written_data[0]["team"] == "Mock Team"
        assert written_data[0]["wins"] == 10
        assert written_data[0]["losses"] == 4
        assert written_data[0]["ties"] == 1
