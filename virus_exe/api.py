from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from virus_exe.config import DATABASE_PATH
from virus_exe.missions.model import MissionResult
from virus_exe.storage.database import Database


class ResultPayload(BaseModel):
    status: str = Field(pattern="^(WON|LOST)$")
    reason: str = Field(min_length=1, max_length=200)
    score: int = Field(ge=0, le=10_000_000)
    duration: float = Field(ge=0, le=86_400)
    total_infection: float = Field(ge=0, le=100)
    detection: float = Field(ge=0, le=100)
    moves: int = Field(ge=0, le=100_000)
    scans: int = Field(ge=0, le=100_000)
    infections: int = Field(ge=0, le=100_000)
    hides: int = Field(ge=0, le=100_000)


class SessionPayload(BaseModel):
    mission_id: str = Field(min_length=1, max_length=80)
    result: ResultPayload


database = Database(DATABASE_PATH)
app = FastAPI(title="Virus.exe API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "virus-exe"}


@app.get("/api/leaderboard")
def leaderboard(limit: int = Query(default=20, ge=1, le=100)) -> list[dict[str, Any]]:
    return database.leaderboard(limit)


@app.get("/api/stats")
def stats() -> dict[str, Any]:
    return database.summary()


@app.get("/api/sessions/{session_id}")
def session(session_id: int) -> dict[str, Any]:
    item = database.get_session(session_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return item


@app.post("/api/sessions", status_code=201)
def create_session(payload: SessionPayload) -> dict[str, int]:
    result = MissionResult(**payload.result.model_dump())
    session_id = database.save_session(payload.mission_id, result)
    return {"id": session_id}


def run_api() -> None:
    uvicorn.run("virus_exe.api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run_api()
