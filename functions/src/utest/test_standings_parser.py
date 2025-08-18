import json

import pytest

from ..standings_parser import (
    Conditions,
    ConferenceGroup,
    Parse,
    TeamStandingInfo,
    find_first,
    parse_team_standing_info,
)


def test_conference_group_no_shared_list():
    a = ConferenceGroup(name="A")
    b = ConferenceGroup(name="B")
    a.add_team(
        TeamStandingInfo(
            name="X",
            abbreviation_name="X",
            wins=1,
            losses=0,
            ties=0,
            win_percentage=1.0,
            points_for=10,
            points_against=3,
            streak=1,
            home_record=(1, 0),
            away_record=(0, 0),
            division_record=(0, 0),
            conference_record=(0, 0),
        )
    )
    assert len(a.teams) == 1
    assert len(b.teams) == 0  # must not share the same list


def _make_stat(name: str, value: str | int):
    if isinstance(value, (int, float)):
        return {"name": name, "value": str(value), "displayValue": str(value)}
    return {"name": name, "value": value, "displayValue": value}


def _make_team(stats):
    return {
        "team": {"displayName": "Example Team", "abbreviation": "EXT"},
        "stats": stats,
    }


def test_parse_team_standing_info_basic():
    stats = [
        _make_stat("wins", 4),
        _make_stat("losses", 2),
        _make_stat("ties", 0),
        _make_stat("winPercent", "0.667"),
        _make_stat("Home", "2-1"),
        _make_stat("Road", "2-1"),
        _make_stat("vs. Div.", "1-1"),
        _make_stat("vs. Conf.", "3-1"),
        _make_stat("pointsFor", 123),
        _make_stat("pointsAgainst", 100),
        _make_stat("streak", 2),
    ]
    team = _make_team(stats)
    parsed = parse_team_standing_info(team)

    assert parsed.name == "Example Team"
    assert parsed.abbreviation_name == "EXT"
    assert parsed.wins == 4
    assert parsed.losses == 2
    assert parsed.ties == 0
    assert parsed.win_percentage == pytest.approx(0.667)
    assert parsed.home_record == (2, 1)
    assert parsed.away_record == (2, 1)
    assert parsed.division_record == (1, 1)
    assert parsed.conference_record == (3, 1)
    assert parsed.points_for == 123
    assert parsed.points_against == 100
    assert parsed.streak == 2
    assert parsed.points_diff == 23


def test_parse_tuple_with_ties_and_weird_dash():
    # Ensure we handle '4-2-1' and en dash gracefully
    assert Parse.tuple_int_value({"displayValue": "4–2–1"}) == (4, 2)
    assert Parse.tuple_int_value({"displayValue": "10-7-0"}) == (10, 7)


def test_find_first_no_match_raises():
    with pytest.raises(ValueError):
        find_first([], Conditions.wins)


def test_model_dump_serialization():
    team = TeamStandingInfo(
        name="Example Team",
        abbreviation_name="EXT",
        wins=4,
        losses=2,
        ties=0,
        win_percentage=0.667,
        home_record=(2, 1),
        away_record=(2, 1),
        division_record=(1, 1),
        conference_record=(3, 1),
        points_for=123,
        points_against=100,
        streak=2,
    )
    group = ConferenceGroup(name="Test")
    group.add_team(team)

    dumped = json.loads(json.dumps(group.model_dump()))
    assert dumped["name"] == "Test"
    assert dumped["teams"][0]["abbreviation_name"] == "EXT"
