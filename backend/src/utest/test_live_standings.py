from unittest.mock import patch

from fastapi.testclient import TestClient

from ..main import app

client = TestClient(app)


def _espn_payload(team_name: str = "Example Team"):
    return {
        "content": {
            "standings": {
                "groups": [
                    {
                        "abbreviation": "AFC",
                        "groups": [
                            {
                                "standings": {
                                    "entries": [
                                        {
                                            "team": {"displayName": team_name},
                                            "stats": [
                                                {"name": "wins", "value": "3"},
                                                {"name": "losses", "value": "1"},
                                            ],
                                        }
                                    ]
                                }
                            }
                        ],
                    }
                ]
            }
        }
    }


@patch("httpx.get")
def test_live_standings_minimal(mock_get):
    mock_get.return_value.json.return_value = _espn_payload("Mock Team")
    mock_get.return_value.raise_for_status.return_value = None

    r = client.get("/standings/live")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(d["team"] == "Mock Team" for d in data)
