"""Local-only API over the imported CPBL SQLite database."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .database import CPBLDatabase

database = CPBLDatabase(Path(__file__).resolve().parents[2] / "data" / "cpbl.sqlite")
app = FastAPI(title="CPBL Analysis", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET"], allow_headers=["*"])


def require_season(season: int) -> None:
    if season not in database.seasons(): raise HTTPException(404, "Season not imported. Run scripts/import_cpbl_sqlite.py first.")


@app.get("/api/health")
def health() -> dict[str, object]: return {"status": "ok", "data_mode": "local-sqlite", "seasons": database.seasons()}


@app.get("/api/seasons")
def seasons() -> list[int]: return database.seasons()


@app.get("/api/league/trend")
def league_trend() -> list[dict[str, object]]: return database.league_trend()


@app.get("/api/teams/summary")
def team_summaries(season: int = Query(..., ge=1990)) -> list[dict[str, object]]:
    require_season(season)
    return database.team_summaries(season)


@app.get("/api/{kind}")
def rows(kind: str, season: int = Query(..., ge=1990), team_id: str | None = None) -> list[dict[str, object]]:
    table = {"batters": "batting", "pitchers": "pitching", "standings": "standings"}.get(kind)
    if not table: raise HTTPException(404, "Unknown dataset")
    require_season(season)
    return database.rows(table, season, team_id)


@app.get("/api/{kind}/player/{player_id}/history")
def history(kind: str, player_id: str) -> list[dict[str, object]]:
    table = {"batters": "batting", "pitchers": "pitching"}.get(kind)
    if not table: raise HTTPException(404, "Unknown dataset")
    return database.player_history(table, player_id)


