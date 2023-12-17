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
        self.assertIn(b"Welcome to NFL Scores and Standings", response.data)


if __name__ == "__main__":
    pytest.main()
