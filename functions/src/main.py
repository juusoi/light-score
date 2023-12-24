import asyncio
import json
import time
from typing import Any, List

from functions.src.espn_integration import ESPN_API
from functions.src.standings_parser import (
    Conditions,
    ConferenceGroup,
    TeamStandingInfo,
    find_first,
    parse_team_standing_info,
)


def convert_to_dict(obj: Any) -> dict:
    if isinstance(obj, (TeamStandingInfo, ConferenceGroup)):
        model = obj.model_dump()
        return model
    return obj


def save_on_disk(conference: List[ConferenceGroup], name: str):
    with open(name, "w", encoding="utf-8") as file:
        json.dump(conference, file, indent=4, default=convert_to_dict)


async def main():
    start_api = time.time_ns()
    espn_api = ESPN_API()
    content = await espn_api.get_standings()

    elapsed_time_seconds = (time.time_ns() - start_api) / 1e9
    print(f"Request time: {elapsed_time_seconds} seconds")
    start = time.time_ns()
    await espn_api.close()

    response_object = json.loads(content)
    conferences = response_object["content"]["standings"]["groups"]

    afc = find_first(conferences, Conditions.american_football_conference)
    nfc = find_first(conferences, Conditions.national_football_conference)

    afc_groups = afc["groups"]
    nfc_groups = nfc["groups"]

    parsed_afc: List[ConferenceGroup] = []
    parsed_nfc: List[ConferenceGroup] = []

    for afc_group, nfc_group in zip(afc_groups, nfc_groups, strict=True):
        afc_group_parsed = ConferenceGroup(name=afc_group["name"])
        nfc_group_parsed = ConferenceGroup(name=nfc_group["name"])

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

    # TODO. Save to firebase db
    save_on_disk(parsed_afc, "afc.json")
    save_on_disk(parsed_nfc, "nfc.json")


if __name__ == "__main__":
    asyncio.run(main())
