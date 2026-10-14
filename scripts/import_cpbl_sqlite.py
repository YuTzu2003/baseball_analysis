"""Import every downloaded CPBL season into a local SQLite database."""

from __future__ import annotations

import csv
from pathlib import Path

from baseball_analysis.database import CPBLDatabase, dump_raw


def integer(row: dict[str, str], key: str) -> int: return int(row.get(key, "0") or 0)
def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source: return list(csv.DictReader(source))
def rate(value: float, denominator: float, digits: int = 3) -> float | None: return round(value / denominator, digits) if denominator else None
def ip_outs(value: str) -> int:
    innings = float(value); return int(innings) * 3 + round((innings - int(innings)) * 10)


def import_batting(database: CPBLDatabase, path: Path, season: int) -> int:
    payload = []
    for row in read(path):
        ab, h, bb, hbp, sf, tb, pa, so = (integer(row, key) for key in ("AB", "H", "BB", "HBP", "SF", "TB", "PA", "SO"))
        obp_base = ab + bb + hbp + sf; avg = rate(h, ab); obp = rate(h + bb + hbp, obp_base); slg = rate(tb, ab)
        payload.append((season, row["ID"], row["Team ID"], row["Name"], row["Team Name"], pa, ab, h, integer(row, "HR"), integer(row, "RBI"), bb, so, integer(row, "SB"), avg, obp, slg, round(obp + slg, 3) if obp is not None and slg is not None else None, rate(so * 100, pa, 1), rate(bb * 100, pa, 1), round(slg - avg, 3) if slg is not None and avg is not None else None, dump_raw(row)))
    database.replace("batting", season, ["season", "player_id", "team_id", "name", "team", "pa", "ab", "h", "hr", "rbi", "bb", "so", "sb", "avg", "obp", "slg", "ops", "k_pct", "bb_pct", "iso", "raw_json"], payload)
    return len(payload)


def import_pitching(database: CPBLDatabase, path: Path, season: int) -> int:
    payload = []
    for row in read(path):
        outs = ip_outs(row["IP"]); innings = outs / 3; h, bb, so, hr, er, bf = (integer(row, key) for key in ("H", "BB", "SO", "HR", "ER", "BF"))
        payload.append((season, row["ID"], row["Team ID"], row["Name"], row["Team Name"], outs, integer(row, "W"), integer(row, "L"), integer(row, "SV"), integer(row, "HLD"), so, bb, hr, er, rate(er * 9, innings, 2), rate(h + bb, innings, 2), rate(so * 100, bf, 1), rate(bb * 100, bf, 1), rate(so * 9, innings, 2), rate(bb * 9, innings, 2), rate(hr * 9, innings, 2), dump_raw(row)))
    database.replace("pitching", season, ["season", "player_id", "team_id", "name", "team", "ip_outs", "w", "l", "sv", "hld", "so", "bb", "hr", "er", "era", "whip", "k_pct", "bb_pct", "k_9", "bb_9", "hr_9", "raw_json"], payload)
    return len(payload)


def import_standings(database: CPBLDatabase, path: Path) -> int:
    seasons: dict[int, list[tuple[object, ...]]] = {}
    for row in read(path):
        season, wins, losses = int(row["Year"]), integer(row, "Win"), integer(row, "Lose")
        seasons.setdefault(season, []).append((season, row["Team ID"], row["Team"], row["Team Nickname"], wins, losses, integer(row, "Tie"), rate(wins, wins + losses)))
    for season, rows in seasons.items(): database.replace("standings", season, ["season", "team_id", "team", "nickname", "wins", "losses", "ties", "win_pct"], rows)
    return sum(map(len, seasons.values()))


def main() -> None:
    root = Path("data/sources/cpbl-opendata/CPBL"); database = CPBLDatabase(Path("data/cpbl.sqlite")); count = {"batting": 0, "pitching": 0}
    for path in sorted((root / "battings").glob("*.csv")):
        season = int(path.stem); count["batting"] += import_batting(database, path, season); count["pitching"] += import_pitching(database, root / "pitchings" / path.name, season)
    count["standings"] = import_standings(database, root / "standings.csv")
    print(f"Imported {count['batting']} batting, {count['pitching']} pitching, {count['standings']} standings rows into {database.path}")


if __name__ == "__main__": main()
