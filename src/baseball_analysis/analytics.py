"""Small, dependency-free CPBL batting calculations and source adapters."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any


def batting_rate(row: dict[str, Any]) -> dict[str, Any]:
    """Return standard rate stats from a cpbl-opendata batting row."""
    ab, h = int(row["AB"]), int(row["H"])
    bb, hbp, sf = int(row["BB"]), int(row["HBP"]), int(row["SF"])
    tb = int(row["TB"])
    pa = ab + bb + hbp + sf
    avg = h / ab if ab else 0
    obp = (h + bb + hbp) / pa if pa else 0
    slg = tb / ab if ab else 0
    return {
        **row,
        "PA_calc": pa,
        "AVG": round(avg, 3),
        "OBP": round(obp, 3),
        "SLG": round(slg, 3),
        "OPS": round(obp + slg, 3),
    }


def load_batting_csv(data_root: Path, season: int) -> list[dict[str, Any]]:
    """Load the public ldkrsi/cpbl-opendata CSV layout without copying its data."""
    path = data_root / "CPBL" / "battings" / f"{season}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No batting file found at {path}")
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = [batting_rate(row) for row in csv.DictReader(source)]
    return sorted(rows, key=lambda row: row["OPS"], reverse=True)


def team_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        team = row["Team Name"]
        for stat in ("AB", "H", "TB", "BB", "HBP", "SF", "HR", "RBI"):
            totals[team][stat] += float(row[stat])
    result = []
    for team, value in totals.items():
        ab = value["AB"]
        obp_den = ab + value["BB"] + value["HBP"] + value["SF"]
        ops = (value["H"] + value["BB"] + value["HBP"]) / obp_den + value["TB"] / ab if ab else 0
        result.append({"team": team, "OPS": round(ops, 3), "HR": int(value["HR"]), "RBI": int(value["RBI"])})
    return sorted(result, key=lambda row: row["OPS"], reverse=True)
