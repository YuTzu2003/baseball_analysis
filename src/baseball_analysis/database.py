"""SQLite schema and read helpers for locally downloaded CPBL datasets."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


class CPBLDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with closing(self.connect()) as connection, connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS batting (
                  season INTEGER NOT NULL, player_id TEXT NOT NULL, team_id TEXT NOT NULL,
                  name TEXT NOT NULL, team TEXT NOT NULL, pa INTEGER NOT NULL, ab INTEGER NOT NULL,
                  h INTEGER NOT NULL, hr INTEGER NOT NULL, rbi INTEGER NOT NULL, bb INTEGER NOT NULL,
                  so INTEGER NOT NULL, sb INTEGER NOT NULL, avg REAL, obp REAL, slg REAL, ops REAL,
                  k_pct REAL, bb_pct REAL, iso REAL, raw_json TEXT NOT NULL,
                  PRIMARY KEY (season, player_id, team_id)
                );
                CREATE TABLE IF NOT EXISTS pitching (
                  season INTEGER NOT NULL, player_id TEXT NOT NULL, team_id TEXT NOT NULL,
                  name TEXT NOT NULL, team TEXT NOT NULL, ip_outs INTEGER NOT NULL, w INTEGER NOT NULL,
                  l INTEGER NOT NULL, sv INTEGER NOT NULL, hld INTEGER NOT NULL, so INTEGER NOT NULL,
                  bb INTEGER NOT NULL, hr INTEGER NOT NULL, er INTEGER NOT NULL, era REAL, whip REAL,
                  k_pct REAL, bb_pct REAL, k_9 REAL, bb_9 REAL, hr_9 REAL, raw_json TEXT NOT NULL,
                  PRIMARY KEY (season, player_id, team_id)
                );
                CREATE TABLE IF NOT EXISTS standings (
                  season INTEGER NOT NULL, team_id TEXT NOT NULL, team TEXT NOT NULL, nickname TEXT,
                  wins INTEGER NOT NULL, losses INTEGER NOT NULL, ties INTEGER NOT NULL, win_pct REAL,
                  PRIMARY KEY (season, team_id)
                );
                CREATE INDEX IF NOT EXISTS idx_batting_season_team ON batting(season, team_id);
                CREATE INDEX IF NOT EXISTS idx_pitching_season_team ON pitching(season, team_id);
            """)

    def seasons(self) -> list[int]:
        self.initialize()
        with closing(self.connect()) as connection:
            return [row[0] for row in connection.execute("SELECT DISTINCT season FROM batting ORDER BY season DESC")]

    def rows(self, table: str, season: int, team_id: str | None = None) -> list[dict[str, Any]]:
        if table not in {"batting", "pitching", "standings"}:
            raise ValueError("Unsupported table")
        self.initialize()
        sql = f"SELECT * FROM {table} WHERE season = ?"
        parameters: list[object] = [season]
        if team_id and team_id != "all":
            sql += " AND team_id = ?"; parameters.append(team_id)
        with closing(self.connect()) as connection:
            return [dict(row) for row in connection.execute(sql, parameters)]

    def player_history(self, table: str, player_id: str) -> list[dict[str, Any]]:
        if table not in {"batting", "pitching"}: raise ValueError("Unsupported table")
        self.initialize()
        with closing(self.connect()) as connection:
            return [dict(row) for row in connection.execute(f"SELECT * FROM {table} WHERE player_id = ? ORDER BY season", (player_id,))]

    def league_trend(self) -> list[dict[str, Any]]:
        """Return count-weighted league batting and pitching indicators by season."""
        self.initialize()
        with closing(self.connect()) as connection:
            return [dict(row) for row in connection.execute("""
                WITH batting_trend AS (
                    SELECT season, ROUND(CAST(SUM(h) AS REAL) / NULLIF(SUM(ab), 0), 3) AS avg, SUM(hr) AS hr
                    FROM batting GROUP BY season
                ), pitching_trend AS (
                    SELECT season, ROUND((CAST(SUM(er) AS REAL) * 27) / NULLIF(SUM(ip_outs), 0), 2) AS era
                    FROM pitching GROUP BY season
                )
                SELECT batting_trend.season, batting_trend.avg, batting_trend.hr, pitching_trend.era
                FROM batting_trend JOIN pitching_trend USING (season) ORDER BY season
            """)]

    def team_summaries(self, season: int) -> list[dict[str, Any]]:
        """Return correctly weighted batting and pitching totals for each team."""
        standings = self.rows("standings", season)
        batting_totals: dict[str, dict[str, int]] = {}
        pitching_totals: dict[str, dict[str, int]] = {}

        for row in self.rows("batting", season):
            total = batting_totals.setdefault(
                row["team_id"],
                {"ab": 0, "h": 0, "hr": 0, "rbi": 0, "bb": 0, "hbp": 0, "sf": 0, "tb": 0},
            )
            source = json.loads(row["raw_json"])
            for key in ("ab", "h", "hr", "rbi", "bb"):
                total[key] += int(row[key])
            total["hbp"] += int(source.get("HBP", 0) or 0)
            total["sf"] += int(source.get("SF", 0) or 0)
            total["tb"] += int(source.get("TB", 0) or 0)

        for row in self.rows("pitching", season):
            total = pitching_totals.setdefault(
                row["team_id"],
                {"ip_outs": 0, "w": 0, "l": 0, "sv": 0, "so": 0, "bb": 0, "h": 0, "er": 0},
            )
            source = json.loads(row["raw_json"])
            for key in ("ip_outs", "w", "l", "sv", "so", "bb", "er"):
                total[key] += int(row[key])
            total["h"] += int(source.get("H", 0) or 0)

        def rate(numerator: int, denominator: int, digits: int) -> float | None:
            return round(numerator / denominator, digits) if denominator else None

        summaries = []
        for club in standings:
            batting = batting_totals.get(
                club["team_id"],
                {"ab": 0, "h": 0, "hr": 0, "rbi": 0, "bb": 0, "hbp": 0, "sf": 0, "tb": 0},
            )
            pitching = pitching_totals.get(
                club["team_id"],
                {"ip_outs": 0, "w": 0, "l": 0, "sv": 0, "so": 0, "bb": 0, "h": 0, "er": 0},
            )
            avg = rate(batting["h"], batting["ab"], 3)
            obp = rate(
                batting["h"] + batting["bb"] + batting["hbp"],
                batting["ab"] + batting["bb"] + batting["hbp"] + batting["sf"],
                3,
            )
            slg = rate(batting["tb"], batting["ab"], 3)
            summaries.append(
                {
                    "team_id": club["team_id"],
                    "team": club["team"],
                    "nickname": club["nickname"],
                    "batting": {
                        "AVG": avg,
                        "OBP": obp,
                        "SLG": slg,
                        "OPS": round(obp + slg, 3) if obp is not None and slg is not None else None,
                        "HR": batting["hr"],
                        "RBI": batting["rbi"],
                    },
                    "pitching": {
                        "ERA": rate(pitching["er"] * 27, pitching["ip_outs"], 2),
                        "WHIP": rate((pitching["h"] + pitching["bb"]) * 3, pitching["ip_outs"], 2),
                        "SO": pitching["so"],
                        "W": pitching["w"],
                        "L": pitching["l"],
                        "SV": pitching["sv"],
                    },
                }
            )
        return summaries

    def replace(self, table: str, season: int, columns: list[str], rows: list[tuple[Any, ...]]) -> None:
        self.initialize()
        marks = ", ".join("?" for _ in columns)
        with closing(self.connect()) as connection, connection:
            connection.execute(f"DELETE FROM {table} WHERE season = ?", (season,))
            connection.executemany(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({marks})", rows)


def dump_raw(row: dict[str, str]) -> str:
    return json.dumps(row, ensure_ascii=False, separators=(",", ":"))
