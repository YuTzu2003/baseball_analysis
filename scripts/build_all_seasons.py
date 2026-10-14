"""Build static JSON snapshots for every CPBL season into frontend/public/data/seasons/."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path


def number(row: dict[str, str], key: str) -> int:
    return int(row.get(key, "0") or 0)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def batters(path: Path) -> list[dict[str, object]]:
    result = []
    if not path.exists():
        return result
    for row in read_rows(path):
        ab, hits, bb, hbp, sf = (number(row, key) for key in ("AB", "H", "BB", "HBP", "SF"))
        tb, so, pa = number(row, "TB"), number(row, "SO"), number(row, "PA")
        avg = hits / ab if ab else None
        obp_denominator = ab + bb + hbp + sf
        obp = (hits + bb + hbp) / obp_denominator if obp_denominator else None
        slg = tb / ab if ab else None
        result.append({
            "source_player_id": row["ID"],
            "source_team_id": row["Team ID"],
            "name": row["Name"],
            "team": row["Team Name"],
            "G": number(row, "G"),
            "PA": pa,
            "AB": ab,
            "R": number(row, "R"),
            "H": hits,
            "HR": number(row, "HR"),
            "RBI": number(row, "RBI"),
            "BB": bb,
            "SO": so,
            "SB": number(row, "SB"),
            "TB": tb,
            "AVG": round(avg, 3) if avg is not None else None,
            "OBP": round(obp, 3) if obp is not None else None,
            "SLG": round(slg, 3) if slg is not None else None,
            "OPS": round(obp + slg, 3) if obp is not None and slg is not None else None,
            "K_pct": round(so / pa * 100, 1) if pa else None,
            "BB_pct": round(bb / pa * 100, 1) if pa else None,
            "ISO": round(slg - avg, 3) if avg is not None and slg is not None else None,
        })
    return result


def pitchers(path: Path) -> list[dict[str, object]]:
    result = []
    if not path.exists():
        return result
    for row in read_rows(path):
        raw_ip = float(row["IP"])
        outs = int(raw_ip) * 3 + round((raw_ip - int(raw_ip)) * 10)
        innings = outs / 3
        er, hits, bb, so, hr, bf = (number(row, key) for key in ("ER", "H", "BB", "SO", "HR", "BF"))
        result.append({
            "source_player_id": row["ID"],
            "source_team_id": row["Team ID"],
            "name": row["Name"],
            "team": row["Team Name"],
            "G": number(row, "G"),
            "W": number(row, "W"),
            "L": number(row, "L"),
            "SV": number(row, "SV"),
            "HLD": number(row, "HLD"),
            "IP": round(innings, 2),
            "SO": so,
            "BB": bb,
            "HR": hr,
            "ER": er,
            "ERA": round(er * 9 / innings, 2) if innings else None,
            "WHIP": round((hits + bb) / innings, 2) if innings else None,
            "K_pct": round(so / bf * 100, 1) if bf else None,
            "BB_pct": round(bb / bf * 100, 1) if bf else None,
            "K_9": round(so * 9 / innings, 2) if innings else None,
            "BB_9": round(bb * 9 / innings, 2) if innings else None,
            "HR_9": round(hr * 9 / innings, 2) if innings else None,
        })
    return result


def standings(path: Path, season: int) -> list[dict[str, object]]:
    result = []
    if not path.exists():
        return result
    for row in read_rows(path):
        if int(row["Year"]) != season:
            continue
        wins, losses, ties = number(row, "Win"), number(row, "Lose"), number(row, "Tie")
        result.append({
            "source_team_id": row["Team ID"],
            "team": row["Team"],
            "nickname": row["Team Nickname"],
            "W": wins,
            "L": losses,
            "T": ties,
            "win_pct": round(wins / (wins + losses), 3) if wins + losses else None,
        })
    return result


def main() -> None:
    source_root = Path("data/sources/cpbl-opendata/CPBL")
    public_dir = Path("frontend/public/data/seasons")
    public_dir.mkdir(parents=True, exist_ok=True)

    batting_files = sorted(source_root.glob("battings/*.csv"))
    seasons = [int(p.stem) for p in batting_files]
    seasons.sort(reverse=True)

    print(f"Found {len(seasons)} seasons: {seasons[-1]} - {seasons[0]}")

    for season in seasons:
        payload = {
            "season": season,
            "generated_at": date.today().isoformat(),
            "source": "ldkrsi/cpbl-opendata",
            "batters": batters(source_root / "battings" / f"{season}.csv"),
            "pitchers": pitchers(source_root / "pitchings" / f"{season}.csv"),
            "standings": standings(source_root / "standings.csv", season),
        }
        target = public_dir / f"{season}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if season == 2024:
            src_target = Path("frontend/src/data/cpbl-2024.json")
            src_target.parent.mkdir(parents=True, exist_ok=True)
            src_target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    (public_dir / "seasons.json").write_text(
        json.dumps(seasons, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Successfully generated all {len(seasons)} season JSONs in {public_dir}")


if __name__ == "__main__":
    main()
