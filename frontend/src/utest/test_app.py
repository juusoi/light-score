import pytest
from app import app
from flask_testing import TestCase


class MyTest(TestCase):
    def create_app(self):
        app.config["TESTING"] = True
        return app

    def test_home_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        # Should render the teletext layout (offline variant when backend not reachable in tests)
        self.assertIn(b"Light Score", response.data)


if __name__ == "__main__":
    pytest.main()
