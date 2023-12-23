import asyncio
import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Tuple

import httpx
from pydantic import BaseModel, computed_field

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8", level=logging.INFO
)


def find_first(list_of_items: List[Dict], condition: Callable[..., bool]) -> Any:
    try:
        return next(filter(condition, list_of_items))
    except Exception as e:
        # pprint(list_of_items, indent=4)
        raise Exception(
            f"Cannot meet the condition {inspect.getsource(condition)}"
        ) from e


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


def parse_team_standing_info(team: dict) -> TeamStandingInfo:
    """Deserialize

    Args:
        o (dict): _description_

    Returns:
        TeamStandingInfo: _description_
    """

    def parse_int_value(obj: dict) -> int:
        return int(float(obj["value"]))

    def parse_tuple_int_value(obj: dict) -> Tuple[int, int]:
        value: str = obj["displayValue"]
        first, second = value.split("-", maxsplit=1)
        return (int(first), int(second))

    name = team["team"]["displayName"]
    abbreviation = team["team"]["abbreviation"]

    stats = team["stats"]
    wins = find_first(stats, lambda item: item["name"] == "wins")
    losses = find_first(stats, lambda item: item["name"] == "losses")
    ties = find_first(stats, lambda item: item["name"] == "ties")
    win_percent = find_first(stats, lambda item: item["name"] == "winPercent")
    home_record = find_first(stats, lambda item: item["name"] == "Home")
    away_record = find_first(stats, lambda item: item["name"] == "Road")
    division_record = find_first(stats, lambda item: item["name"] == "vs. Div.")
    conference_record = find_first(stats, lambda item: item["name"] == "vs. Conf.")
    points_for = find_first(stats, lambda item: item["name"] == "pointsFor")
    points_against = find_first(stats, lambda item: item["name"] == "pointsAgainst")
    streak = find_first(stats, lambda item: item["name"] == "streak")

    return TeamStandingInfo(
        name=name,
        abbreviation_name=abbreviation,
        wins=parse_int_value(wins),
        losses=parse_int_value(losses),
        ties=parse_int_value(ties),
        win_percentage=float(win_percent["value"]),
        home_record=parse_tuple_int_value(home_record),
        away_record=parse_tuple_int_value(away_record),
        division_record=parse_tuple_int_value(division_record),
        conference_record=parse_tuple_int_value(conference_record),
        points_for=parse_int_value(points_for),
        points_against=parse_int_value(points_against),
        streak=parse_int_value(streak),
    )


async def main():
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

    response_object = json.loads(content)
    conferences = response_object["content"]["standings"]["groups"]

    afc = find_first(
        conferences, lambda conference: conference["abbreviation"] == "AFC"
    )
    nfc = find_first(
        conferences, lambda conference: conference["abbreviation"] == "NFC"
    )

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

    # pprint(parsed_afc, indent=4)
    # pprint(parsed_nfc, indent=4)

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
