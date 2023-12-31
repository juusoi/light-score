import logging

import httpx


class EspnClient:
    standings_url = "https://cdn.espn.com/core/nfl/standings?xhr=1"
    client: httpx.AsyncClient

    def __init__(self):
        self.client = httpx.AsyncClient()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exception_type, exception_value, exception_traceback):
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
