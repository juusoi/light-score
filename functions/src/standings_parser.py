import asyncio
import json
import logging
import time
from operator import itemgetter
from typing import Any, Callable, Dict, List, Tuple

import httpx
from pydantic import BaseModel, computed_field

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8", level=logging.INFO
)


class TeamStandingInfo(BaseModel):
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
    @property
    def points_diff(self) -> int:
        return self.points_for - self.points_against


class ConferenceGroup(BaseModel):
    name: str
    teams: List[TeamStandingInfo]

    def add_team(self, team: TeamStandingInfo):
        self.teams.append(team)


class Conditions:
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
    try:
        return next(filter(condition, list_of_items))
    except StopIteration as e:
        logging.error(list_of_items)
        raise Exception("No item found with the given condition") from e


class Parse:
    @staticmethod
    def int_value(obj: dict) -> int:
        return int(float(obj["value"]))

    @staticmethod
    def tuple_int_value(obj: dict) -> Tuple[int, int]:
        value: str = obj["displayValue"]
        first, second = value.split("-", maxsplit=1)
        return (int(first), int(second))


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


async def main():
    start_api = time.time_ns()
    espn_standings_url = "https://cdn.espn.com/core/nfl/standings?xhr=1"

    async with httpx.AsyncClient() as client:
        response = await client.get(espn_standings_url)

        if response.is_error:
            logging.error(
                f"Request failed: {response.url}, {response.status_code}, {response.text}"
            )
            response.close()
            return

        content = await response.aread()

    elapsed_time_seconds = (time.time_ns() - start_api) / 1e9
    print(f"Request time: {elapsed_time_seconds} seconds")
    start = time.time_ns()

    response_object = json.loads(content)
    conferences = response_object["content"]["standings"]["groups"]

    afc = find_first(conferences, Conditions.american_football_conference)
    nfc = find_first(conferences, Conditions.national_football_conference)

    afc_groups = afc["groups"]
    nfc_groups = nfc["groups"]

    parsed_afc: List[ConferenceGroup] = list()
    parsed_nfc: List[ConferenceGroup] = list()

    for afc_group, nfc_group in zip(afc_groups, nfc_groups, strict=True):
        afc_group_parsed = ConferenceGroup(name=afc_group["name"], teams=list())
        nfc_group_parsed = ConferenceGroup(name=nfc_group["name"], teams=list())

        afc_entries = afc_group["standings"]["entries"]
        nfc_entries = nfc_group["standings"]["entries"]

        for afc_team, nfc_team in zip(afc_entries, nfc_entries, strict=True):
            parsed_afc_team = parse_team_standing_info(afc_team)
            parsed_nfc_team = parse_team_standing_info(nfc_team)

            afc_group_parsed.add_team(parsed_afc_team)
            nfc_group_parsed.add_team(parsed_nfc_team)

        parsed_afc.append(afc_group_parsed)
        parsed_nfc.append(nfc_group_parsed)

    elapsed_time_seconds = (time.time_ns() - start) / 1e9
    print(f"Parser time: {elapsed_time_seconds} seconds")

    def convert_to_dict(obj: Any) -> dict:
        if isinstance(obj, (TeamStandingInfo, ConferenceGroup)):
            model = obj.model_dump()
            return model
        return obj

    with open("afc.json", "w", encoding="utf-8") as file:
        json.dump(parsed_afc, file, indent=4, default=convert_to_dict)

    with open("nfc.json", "w", encoding="utf-8") as file:
        json.dump(parsed_nfc, file, indent=4, default=convert_to_dict)


if __name__ == "__main__":
    asyncio.run(main())
