import asyncio
import json
import logging
import time
from pathlib import Path

from .espn_integration import EspnClient
from .standings_parser import (
    Conditions,
    ConferenceGroup,
    find_first,
    parse_team_standing_info,
)


def save_standings_cache(
    parsed_afc: list[ConferenceGroup], parsed_nfc: list[ConferenceGroup]
):
    """Write a minimal standings cache JSON for the backend to serve.

    The format is a list of objects: {"team": str, "wins": int, "losses": int, "ties": int}
    Saved to backend/src/data/standings_cache.json relative to repo root.
    """
    minimal: list[dict] = []

    def add_group(group: ConferenceGroup):
        for t in group.teams:
            minimal.append(
                {
                    "team": t.name,
                    "wins": t.wins,
                    "losses": t.losses,
                    "ties": t.ties,
                }
            )

    for g in parsed_afc:
        add_group(g)
    for g in parsed_nfc:
        add_group(g)

    # Compute repo root from this file location: functions/src/main.py -> repo_root
    repo_root = Path(__file__).resolve().parents[2]
    cache_path = repo_root / "backend" / "src" / "data" / "standings_cache.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(minimal, indent=2), encoding="utf-8")


async def main():
    try:
        start_api = time.time_ns()

        async with EspnClient() as client:
            content = await client.get_standings()

        elapsed_time_seconds = (time.time_ns() - start_api) / 1e9
        logging.info("Request time: %s seconds", elapsed_time_seconds)

        start = time.time_ns()

        response_object = json.loads(content)
        content_data = response_object.get("content")
        if not content_data or not isinstance(content_data, dict):
            raise ValueError("ESPN response missing 'content' field")
        standings_data = content_data.get("standings")
        if not standings_data or not isinstance(standings_data, dict):
            raise ValueError("ESPN response missing 'standings' field")
        conferences = standings_data.get("groups")
        if not conferences:
            raise ValueError("ESPN response missing 'groups' field")

        afc = find_first(conferences, Conditions.american_football_conference)
        nfc = find_first(conferences, Conditions.national_football_conference)

        afc_groups = afc["groups"]
        nfc_groups = nfc["groups"]

        parsed_afc: list[ConferenceGroup] = []
        parsed_nfc: list[ConferenceGroup] = []

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
        logging.info("Parser time: %s seconds", elapsed_time_seconds)

        # Save quick cache for backend e2e testing
        save_standings_cache(parsed_afc, parsed_nfc)
    except Exception:
        logging.exception("Failed to fetch/parse standings")
        raise


if __name__ == "__main__":
    asyncio.run(main())
