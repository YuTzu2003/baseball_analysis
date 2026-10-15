import unittest

from baseball_analysis.app import app


class AppRoutesTest(unittest.TestCase):
    def test_exposes_team_summary_route(self) -> None:
        self.assertIn("/api/teams/summary", {route.path for route in app.routes})


if __name__ == "__main__":
    unittest.main()
