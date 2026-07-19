"""FastAPI application for CausalPilot's local, API-key-free demo."""

from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .schemas import (
    EpisodeSnapshot,
    ErrorResponse,
    HealthResponse,
    HumanAnswerRequest,
    InjectDriftRequest,
    ResetMissionRequest,
    StartMissionRequest,
    StepMissionRequest,
)
from .store import MissionNotFound, store


app = FastAPI(
    title="CausalPilot TRACE API",
    summary="Evidence-gated action rights for causal business experimentation",
    description=(
        "A deterministic, API-key-free implementation of trajectory-aware, risk-index-gated "
        "agentic causal experimentation. Interactive documentation is available at /docs."
    ),
    version="0.1.0",
    openapi_tags=[
        {"name": "system", "description": "Service health"},
        {"name": "mission", "description": "Stateful TRACE experiment episodes"},
    ],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _mission_or_404(mission_id: str):
    try:
        return store.get(mission_id)
    except MissionNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' was not found") from exc


def _bad_transition(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(exc))


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="causalpilot",
        version=app.version,
        deterministic_mode=True,
    )


@app.post(
    "/api/v1/mission/start",
    response_model=EpisodeSnapshot,
    responses={422: {"model": ErrorResponse}},
    tags=["mission"],
)
def start_mission(request: StartMissionRequest) -> EpisodeSnapshot:
    return store.create(request).snapshot()


@app.post(
    "/api/v1/mission/step",
    response_model=EpisodeSnapshot,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    tags=["mission"],
)
def step_mission(request: StepMissionRequest) -> EpisodeSnapshot:
    mission = _mission_or_404(request.mission_id)
    try:
        return mission.execute(request.requested_action, segment_id=request.segment_id)
    except ValueError as exc:
        raise _bad_transition(exc) from exc


@app.post(
    "/api/v1/mission/drift",
    response_model=EpisodeSnapshot,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    tags=["mission"],
)
def inject_drift(request: InjectDriftRequest) -> EpisodeSnapshot:
    mission = _mission_or_404(request.mission_id)
    try:
        return mission.inject_drift(request.severity, request.segment_id)
    except ValueError as exc:
        raise _bad_transition(exc) from exc


@app.post(
    "/api/v1/mission/human-answer",
    response_model=EpisodeSnapshot,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    tags=["mission"],
)
def answer_human(request: HumanAnswerRequest) -> EpisodeSnapshot:
    mission = _mission_or_404(request.mission_id)
    try:
        return mission.answer_human(
            request.answer, margin_floor=request.margin_floor, subsidy_cap=request.subsidy_cap
        )
    except ValueError as exc:
        raise _bad_transition(exc) from exc


@app.post(
    "/api/v1/mission/reset",
    response_model=EpisodeSnapshot,
    responses={404: {"model": ErrorResponse}},
    tags=["mission"],
)
def reset_mission(request: ResetMissionRequest) -> EpisodeSnapshot:
    try:
        return store.reset(request.mission_id).snapshot()
    except MissionNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Mission '{request.mission_id}' was not found") from exc


@app.get(
    "/api/v1/mission/{mission_id}",
    response_model=EpisodeSnapshot,
    responses={404: {"model": ErrorResponse}},
    tags=["mission"],
)
def get_mission(mission_id: str) -> EpisodeSnapshot:
    return _mission_or_404(mission_id).snapshot()


@app.get("/api/v1/mission/{mission_id}/events", tags=["mission"])
def mission_events(mission_id: str) -> StreamingResponse:
    mission = _mission_or_404(mission_id)

    async def event_stream():
        for event in mission.audit_snapshot():
            payload = event.model_dump(mode="json")
            yield f"id: {event.sequence}\nevent: audit\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(0)
        yield "event: end\ndata: {\"caught_up\": true}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
