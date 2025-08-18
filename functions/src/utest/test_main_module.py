import json
from pathlib import Path

from ..main import convert_to_dict, save_on_disk
from ..standings_parser import ConferenceGroup, TeamStandingInfo


def test_convert_to_dict_serializes_models():
    team = TeamStandingInfo(
        name="T",
        abbreviation_name="TT",
        wins=1,
        losses=2,
        ties=0,
        win_percentage=0.333,
        points_for=10,
        points_against=20,
        streak=-1,
        home_record=(1, 0),
        away_record=(0, 2),
        division_record=(0, 1),
        conference_record=(0, 2),
    )
    group = ConferenceGroup(name="G")
    group.add_team(team)

    d_team = convert_to_dict(team)
    d_group = convert_to_dict(group)
    assert isinstance(d_team, dict)
    assert isinstance(d_group, dict)
    assert d_team["abbreviation_name"] == "TT"
    assert d_group["name"] == "G"


def test_save_on_disk_writes_json(tmp_path: Path):
    team = TeamStandingInfo(
        name="T",
        abbreviation_name="TT",
        wins=1,
        losses=2,
        ties=0,
        win_percentage=0.333,
        points_for=10,
        points_against=20,
        streak=-1,
        home_record=(1, 0),
        away_record=(0, 2),
        division_record=(0, 1),
        conference_record=(0, 2),
    )
    group = ConferenceGroup(name="G")
    group.add_team(team)

    out = tmp_path / "out.json"
    save_on_disk([group], str(out))

    data = json.loads(out.read_text())
    assert isinstance(data, list)
    assert data[0]["name"] == "G"
