import logging

import httpx


class ESPN_API:
    standings_url = "https://cdn.espn.com/core/nfl/standings?xhr=1"
    client: httpx.AsyncClient

    def __init__(self):
        self.client = httpx.AsyncClient()

    async def close(self):
        await self.client.aclose()

    async def get_standings(self) -> bytes:
        response = await self.client.get(self.standings_url)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logging.error(
                f"Request failed: {response.url}, {response.status_code}, {response.text}"
            )
            raise e

        return await response.aread()
