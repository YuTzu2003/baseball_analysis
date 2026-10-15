"""Export the full local CPBL dataset as JSON files for static hosting."""

from __future__ import annotations

import json
from pathlib import Path

from baseball_analysis.database import CPBLDatabase


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    database = CPBLDatabase(Path("data/cpbl.sqlite"))
    output = Path("frontend/public/data")
    seasons = database.seasons()
    write_json(output / "seasons.json", seasons)

    player_ids: dict[str, set[str]] = {"batters": set(), "pitchers": set()}
    for season in seasons:
        batters = database.rows("batting", season)
        pitchers = database.rows("pitching", season)
        write_json(
            output / "seasons" / f"{season}.json",
            {
                "batters": batters,
                "pitchers": pitchers,
                "standings": database.rows("standings", season),
                "team_summaries": database.team_summaries(season),
            },
        )
        player_ids["batters"].update(str(row["player_id"]) for row in batters)
        player_ids["pitchers"].update(str(row["player_id"]) for row in pitchers)

    for kind, table in (("batters", "batting"), ("pitchers", "pitching")):
        for player_id in player_ids[kind]:
            write_json(
                output / "players" / kind / f"{player_id}.json",
                database.player_analysis(table, player_id),
            )

    print(f"Exported {len(seasons)} seasons and {sum(map(len, player_ids.values()))} player analyses.")


if __name__ == "__main__":
    main()
