from typing import List

from data.example import example_data
from fastapi import FastAPI
from pydantic import BaseModel

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
    return example_data["standings"]
