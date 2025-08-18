import pytest
from flask_testing import TestCase

from app import app


class MyTest(TestCase):
    def create_app(self):
        app.config["TESTING"] = True
        return app

    def test_home_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        # Should render the teletext layout (offline variant when backend not reachable in tests)
        self.assertIn(b"Light Score", response.data)


def test_season_type_name():
    """Test the season_type_name function."""
    from app import season_type_name

    assert season_type_name(1) == "Preseason"
    assert season_type_name(2) == "Regular Season"
    assert season_type_name(3) == "Postseason"
    assert season_type_name(999) == "Unknown"


if __name__ == "__main__":
    pytest.main()
