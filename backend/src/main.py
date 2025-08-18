import json
from pathlib import Path
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

from data.example import example_data

app = FastAPI()


class Game(BaseModel):
    team_a: str
    team_b: str
    score_a: int
    score_b: int


class Standings(BaseModel):
    team: str
    wins: int
    losses: int


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/games", response_model=List[Game])
def get_games():
    return example_data["games"]


@app.get("/standings", response_model=List[Standings])
def get_standings():
    # Serve from cache file if available; fallback to example data
    cache_file = Path(__file__).resolve().parent / "data" / "standings_cache.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            # If cache is corrupt, fall back to example
            pass
    return example_data["standings"]
