from fastapi.testclient import TestClient

from ..main import app

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}


def test_get_games():
    response = client.get("/games")
    assert response.status_code == 200
    # Add more assertions here based on your example_data structure
    # For example:
    assert "team_a" in response.json()[0]
    assert "score_a" in response.json()[0]


def test_get_standings():
    response = client.get("/standings")
    assert response.status_code == 200
    # Similar to the above, add assertions based on your expected data structure
    # Example:
    assert "team" in response.json()[0]
    assert "wins" in response.json()[0]
