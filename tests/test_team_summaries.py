import json
import tempfile
import unittest
from pathlib import Path

from baseball_analysis.database import CPBLDatabase


class TeamSummariesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.database = CPBLDatabase(Path(self.temporary_directory.name) / "cpbl.sqlite")
        self.database.initialize()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_aggregates_team_totals_and_weighted_rates(self) -> None:
        self.database.replace(
            "standings",
            2024,
            ["season", "team_id", "team", "nickname", "wins", "losses", "ties", "win_pct"],
            [(2024, "AAA", "測試隊", "測試", 10, 8, 2, 0.556)],
        )
        self.database.replace(
            "batting",
            2024,
            [
                "season", "player_id", "team_id", "name", "team", "pa", "ab", "h", "hr", "rbi",
                "bb", "so", "sb", "avg", "obp", "slg", "ops", "k_pct", "bb_pct", "iso", "raw_json",
            ],
            [
                (2024, "b1", "AAA", "打者一", "測試隊", 14, 10, 4, 1, 3, 2, 2, 0, 0.4, 0.5, 0.7, 1.2, 14.3, 14.3, 0.3, json.dumps({"HBP": 1, "SF": 1, "TB": 7})),
                (2024, "b2", "AAA", "打者二", "測試隊", 22, 20, 5, 2, 4, 1, 4, 0, 0.25, 0.286, 0.4, 0.686, 18.2, 4.5, 0.15, json.dumps({"HBP": 0, "SF": 1, "TB": 8})),
            ],
        )
        self.database.replace(
            "pitching",
            2024,
            [
                "season", "player_id", "team_id", "name", "team", "ip_outs", "w", "l", "sv", "hld",
                "so", "bb", "hr", "er", "era", "whip", "k_pct", "bb_pct", "k_9", "bb_9", "hr_9", "raw_json",
            ],
            [
                (2024, "p1", "AAA", "投手一", "測試隊", 15, 1, 0, 0, 0, 6, 1, 0, 2, 3.6, 1.0, 0, 0, 10.8, 1.8, 0, json.dumps({"H": 4})),
                (2024, "p2", "AAA", "投手二", "測試隊", 12, 0, 1, 1, 0, 4, 2, 1, 1, 2.25, 1.25, 0, 0, 9.0, 4.5, 2.25, json.dumps({"H": 3})),
            ],
        )

        self.assertEqual(
            self.database.team_summaries(2024),
            [
                {
                    "team_id": "AAA",
                    "team": "測試隊",
                    "nickname": "測試",
                    "batting": {"AVG": 0.3, "OBP": 0.361, "SLG": 0.5, "OPS": 0.861, "HR": 3, "RBI": 7},
                    "pitching": {"ERA": 3.0, "WHIP": 1.11, "SO": 10, "W": 1, "L": 1, "SV": 1},
                }
            ],
        )

    def test_returns_empty_rate_values_when_a_team_has_no_denominator(self) -> None:
        self.database.replace(
            "standings",
            2024,
            ["season", "team_id", "team", "nickname", "wins", "losses", "ties", "win_pct"],
            [(2024, "EMPTY", "空白隊", "空白", 0, 0, 0, None)],
        )

        [summary] = self.database.team_summaries(2024)

        self.assertEqual(summary["batting"], {"AVG": None, "OBP": None, "SLG": None, "OPS": None, "HR": 0, "RBI": 0})
        self.assertEqual(summary["pitching"], {"ERA": None, "WHIP": None, "SO": 0, "W": 0, "L": 0, "SV": 0})


if __name__ == "__main__":
    unittest.main()
