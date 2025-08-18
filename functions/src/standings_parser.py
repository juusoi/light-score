import logging
import re
from operator import itemgetter
from typing import Any, Callable, Dict, List, Tuple

from pydantic import BaseModel, Field, computed_field

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8", level=logging.INFO
)


class TeamStandingInfo(BaseModel):
    """Represents the standing information for a team."""

    name: str
    abbreviation_name: str
    wins: int
    losses: int
    ties: int
    win_percentage: float
    points_for: int
    points_against: int
    streak: int
    home_record: Tuple[int, int]
    away_record: Tuple[int, int]
    division_record: Tuple[int, int]
    conference_record: Tuple[int, int]

    @computed_field
    def points_diff(self) -> int:
        return self.points_for - self.points_against


class ConferenceGroup(BaseModel):
    """Represents a group of teams within a conference."""

    name: str
    # Use default_factory to avoid sharing the list between instances
    teams: List[TeamStandingInfo] = Field(default_factory=list)

    def add_team(self, team: TeamStandingInfo):
        self.teams.append(team)


class Conditions:
    """Provides conditions for filtering NFL team standing information.

    This class defines static methods, each representing a specific condition
    used for filtering team standing information based on different attributes."""

    _get_name = itemgetter("name")
    _get_abbreviation = itemgetter("abbreviation")

    @staticmethod
    def wins(item: dict) -> bool:
        return Conditions._get_name(item) == "wins"

    @staticmethod
    def losses(item: dict) -> bool:
        return Conditions._get_name(item) == "losses"

    @staticmethod
    def ties(item: dict) -> bool:
        return Conditions._get_name(item) == "ties"

    @staticmethod
    def win_percentage(item: dict) -> bool:
        return Conditions._get_name(item) == "winPercent"

    @staticmethod
    def home_record(item: dict) -> bool:
        return Conditions._get_name(item) == "Home"

    @staticmethod
    def away_record(item: dict) -> bool:
        return Conditions._get_name(item) == "Road"

    @staticmethod
    def division_record(item: dict) -> bool:
        return Conditions._get_name(item) == "vs. Div."

    @staticmethod
    def conference_record(item: dict) -> bool:
        return Conditions._get_name(item) == "vs. Conf."

    @staticmethod
    def points_for(item: dict) -> bool:
        return Conditions._get_name(item) == "pointsFor"

    @staticmethod
    def points_against(item: dict) -> bool:
        return Conditions._get_name(item) == "pointsAgainst"

    @staticmethod
    def streak(item: dict) -> bool:
        return Conditions._get_name(item) == "streak"

    @staticmethod
    def american_football_conference(item: dict) -> bool:
        return Conditions._get_abbreviation(item) == "AFC"

    @staticmethod
    def national_football_conference(item: dict) -> bool:
        return Conditions._get_abbreviation(item) == "NFC"


def find_first(list_of_items: List[Dict], condition: Callable[[Dict], bool]) -> Any:
    """Find the first item in a list that satisfies the given condition."""
    try:
        return next(filter(condition, list_of_items))
    except StopIteration:
        logging.error(list_of_items)
        raise ValueError("No item found with the given condition") from None


class Parse:
    """A utility class for parsing values from dictionaries.

    This class provides static methods for parsing specific types of values from dictionary objects."""

    @staticmethod
    def int_value(obj: dict) -> int:
        return int(float(obj["value"]))

    @staticmethod
    def tuple_int_value(obj: dict) -> Tuple[int, int]:
        """Parse records like '4-2' or '4-2-1' into a (wins, losses) tuple.

        ESPN sometimes includes ties as a third number (e.g., '4-2-1').
        We return the first two components (wins, losses) and ignore the rest.
        """
        value: str = obj["displayValue"]
        # Normalize any en dashes and extract numbers only
        numbers = re.findall(r"\d+", value.replace("–", "-"))
        if len(numbers) < 2:
            raise ValueError(f"Invalid record format: {value}")
        return (int(numbers[0]), int(numbers[1]))


def parse_team_standing_info(team: dict) -> TeamStandingInfo:
    """Deserialize team standing information from a dictionary.

    Args:
        team (dict): A dictionary containing information about a sports team's standing.

    Returns:
        TeamStandingInfo: An instance of the TeamStandingInfo model representing
        the deserialized team standing information.

    The function extracts relevant data from the input dictionary, such as the team's
    name, abbreviation, and various statistics, and constructs a TeamStandingInfo object.
    The statistics are obtained using the find_first function with specific conditions
    defined in the Conditions class.
    """
    name = team["team"]["displayName"]
    abbreviation = team["team"]["abbreviation"]

    stats = team["stats"]

    wins = find_first(stats, Conditions.wins)
    losses = find_first(stats, Conditions.losses)
    ties = find_first(stats, Conditions.ties)
    win_percent = find_first(stats, Conditions.win_percentage)
    home_record = find_first(stats, Conditions.home_record)
    away_record = find_first(stats, Conditions.away_record)
    division_record = find_first(stats, Conditions.division_record)
    conference_record = find_first(stats, Conditions.conference_record)
    points_for = find_first(stats, Conditions.points_for)
    points_against = find_first(stats, Conditions.points_against)
    streak = find_first(stats, Conditions.streak)

    return TeamStandingInfo(
        name=name,
        abbreviation_name=abbreviation,
        wins=Parse.int_value(wins),
        losses=Parse.int_value(losses),
        ties=Parse.int_value(ties),
        win_percentage=float(win_percent["value"]),
        home_record=Parse.tuple_int_value(home_record),
        away_record=Parse.tuple_int_value(away_record),
        division_record=Parse.tuple_int_value(division_record),
        conference_record=Parse.tuple_int_value(conference_record),
        points_for=Parse.int_value(points_for),
        points_against=Parse.int_value(points_against),
        streak=Parse.int_value(streak),
    )
