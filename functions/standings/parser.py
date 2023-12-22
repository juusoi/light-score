import asyncio
import json
import logging

import httpx

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8", level=logging.INFO
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

    afc = next(
        filter(lambda conference: conference["abbreviation"] == "AFC", conferences)
    )
    nfc = next(
        filter(lambda conference: conference["abbreviation"] == "NFC", conferences)
    )

    print(afc)
    print(nfc)


if __name__ == "__main__":
    asyncio.run(main())
