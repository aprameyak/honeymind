from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from models.database import get_db
from models.db import (
    Session,
    Event,
    Cluster,
    AnomalyScore,
    Experiment,
    DeceptionArtifact,
    DeceptionInteraction,
    ActorLabelRow,
)
from models.schemas import (
    EventIngest,
    EventOut,
    SessionOut,
    SessionDetail,
    OverviewOut,
    ClusterOut,
    AnomalyOut,
    ExperimentOut,
    DeceptionRequest,
    DeceptionResponse,
    AnalysisSummary,
    RecomputeResult,
)
from services.analysis import TelemetryService, AnalysisService
from deception.engine import DeceptionEngine
from deception.policy import DeceptionPolicy

logger = logging.getLogger("honeymind")
handler = logging.StreamHandler()
try:
    from pythonjsonlogger.json import JsonFormatter

    handler.setFormatter(JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
except Exception:
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
logger.handlers = [handler]
logger.setLevel(logging.INFO)

app = FastAPI(title="HoneyMind API", version="1.0.0", default_response_class=ORJSONResponse)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rate_buckets: dict[str, deque] = defaultdict(deque)
deception_engine = DeceptionEngine()
deception_policy = DeceptionPolicy()


@app.middleware("http")
async def containment_middleware(request: Request, call_next):
    # Request size limit — reduces DoS via oversized attacker payloads.
    cl = request.headers.get("content-length")
    if cl and int(cl) > settings.max_request_bytes:
        return ORJSONResponse({"detail": "request too large"}, status_code=413)

    client = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _rate_buckets[client]
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit_per_minute:
        return ORJSONResponse({"detail": "rate limit exceeded"}, status_code=429)
    bucket.append(now)

    response: Response = await call_next(request)
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.honeymind_env}


@app.post("/ingest/events")
async def ingest_event(payload: EventIngest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    svc = TelemetryService(db)
    session, event = await svc.ingest(payload)
    logger.info("event_ingested", extra={"session_id": str(session.id), "action": event.action[:80]})
    return {"session_id": str(session.id), "event_id": str(event.id)}


@app.post("/deception/respond", response_model=DeceptionResponse)
async def deception_respond(req: DeceptionRequest, db: AsyncSession = Depends(get_db)) -> DeceptionResponse:
    session_id = req.session_id or uuid.uuid4()
    decision = deception_policy.select(
        session_state={
            "session_depth": req.behavior_hints.get("session_depth", len(req.history)),
            "semantic_actions": req.behavior_hints.get("semantic_actions", []),
            "deception_mode": req.deception_mode,
        },
        behavior_features=req.behavior_hints.get("features"),
        anomaly_score=req.behavior_hints.get("anomaly_score"),
        previous_deception=req.behavior_hints.get("previous_deception", []),
    )
    env = deception_engine.get_env(str(session_id), req.hostname)
    if decision.increase_depth:
        env.increase_depth()
    for path in decision.expose_artifacts:
        if path not in env.exposed_artifacts:
            env.exposed_artifacts.append(path)

    result = deception_engine.generate_response(
        session_id=str(session_id),
        command=req.command,
        hostname=req.hostname,
        history=req.history,
        strategy=decision.strategy,
    )
    return DeceptionResponse(
        session_id=session_id,
        response=result.response,
        response_type=result.response_type,
        strategy=decision.strategy,
        artifacts_exposed=result.artifacts_exposed or decision.expose_artifacts,
        environment_facts=result.environment.facts,
    )


@app.get("/sessions", response_model=list[SessionOut])
async def list_sessions(limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[SessionOut]:
    svc = TelemetryService(db)
    sessions = await svc.list_sessions(limit=limit)
    out: list[SessionOut] = []
    for s in sessions:
        events = await svc.get_events(s.id)
        anomaly = await db.get(AnomalyScore, s.id)
        label = await db.get(ActorLabelRow, s.id)
        out.append(
            SessionOut(
                id=s.id,
                service=s.service,
                started_at=s.started_at,
                ended_at=s.ended_at,
                actor_label=s.actor_label,
                cluster_id=s.cluster_id,
                deception_mode=s.deception_mode,
                metadata=s.metadata_json or {},
                event_count=len(events),
                anomaly_score=anomaly.score if anomaly else None,
                experimental_classification=label.label if label else s.actor_label,
                confidence=label.confidence if label else None,
            )
        )
    return out


@app.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> SessionDetail:
    svc = TelemetryService(db)
    session = await svc.get_session(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    events = session.events or []
    anomaly = session.anomaly
    label = session.actor_label_row
    feats = session.features
    interactions = (
        await db.execute(select(DeceptionInteraction).where(DeceptionInteraction.session_id == session_id))
    ).scalars().all()
    artifact_names = []
    for ix in interactions:
        art = await db.get(DeceptionArtifact, ix.artifact_id)
        if art:
            artifact_names.append(art.name)
    return SessionDetail(
        id=session.id,
        service=session.service,
        started_at=session.started_at,
        ended_at=session.ended_at,
        actor_label=session.actor_label,
        cluster_id=session.cluster_id,
        deception_mode=session.deception_mode,
        metadata=session.metadata_json or {},
        event_count=len(events),
        anomaly_score=anomaly.score if anomaly else None,
        experimental_classification=label.label if label else session.actor_label,
        confidence=label.confidence if label else None,
        semantic_actions=feats.semantic_actions if feats else [],
        session_summary=feats.session_summary if feats else "",
        feature_vector=feats.feature_vector if feats else {},
        artifacts_accessed=artifact_names,
    )


@app.get("/sessions/{session_id}/events", response_model=list[EventOut])
async def get_session_events(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[EventOut]:
    svc = TelemetryService(db)
    session = await svc.get_session(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    events = await svc.get_events(session_id)
    return [
        EventOut(
            id=e.id,
            session_id=e.session_id,
            timestamp=e.timestamp,
            service=e.service,
            action_type=e.action_type,
            action=e.action,
            response_type=e.response_type,
            response_preview=e.response_preview,
            latency_ms=e.latency_ms,
            session_depth=e.session_depth,
            metadata=e.metadata_json or {},
        )
        for e in events
    ]


@app.get("/analytics/overview", response_model=OverviewOut)
async def analytics_overview(db: AsyncSession = Depends(get_db)) -> OverviewOut:
    data = await AnalysisService(db, seed=settings.random_seed).overview()
    return OverviewOut(**data)


@app.get("/analytics/clusters", response_model=list[ClusterOut])
async def analytics_clusters(db: AsyncSession = Depends(get_db)) -> list[ClusterOut]:
    rows = (await db.execute(select(Cluster).order_by(Cluster.external_id))).scalars().all()
    return [
        ClusterOut(
            id=r.id,
            external_id=r.external_id,
            size=r.size,
            common_behaviors=r.common_behaviors or {},
            representative_session_ids=[uuid.UUID(str(x)) for x in (r.representative_session_ids or [])],
        )
        for r in rows
        if r.external_id != -1
    ]


@app.get("/analytics/anomalies", response_model=list[AnomalyOut])
async def analytics_anomalies(db: AsyncSession = Depends(get_db)) -> list[AnomalyOut]:
    rows = (
        await db.execute(select(AnomalyScore).order_by(AnomalyScore.score.desc()).limit(100))
    ).scalars().all()
    out = []
    for r in rows:
        session = await db.get(Session, r.session_id)
        out.append(
            AnomalyOut(
                session_id=r.session_id,
                score=r.score,
                is_anomaly=r.is_anomaly,
                feature_contributions=r.feature_contributions or {},
                service=session.service if session else None,
                actor_label=session.actor_label if session else None,
            )
        )
    return out


@app.get("/analytics/pca")
async def analytics_pca(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    # Lightweight recompute coords from stored normalized features + embeddings for viz.
    svc = AnalysisService(db, seed=settings.random_seed)
    # Return last overview-compatible structure via on-demand clustering coords if features exist.
    result = await db.execute(
        select(Session).options(selectinload(Session.features), selectinload(Session.embeddings))
    )
    sessions = list(result.scalars().all())
    points = []
    for s in sessions:
        points.append(
            {
                "session_id": str(s.id),
                "cluster_id": str(s.cluster_id) if s.cluster_id else None,
                "actor_label": s.actor_label,
                "service": s.service,
            }
        )
    return {"points": points}


@app.get("/experiments", response_model=list[ExperimentOut])
async def list_experiments(db: AsyncSession = Depends(get_db)) -> list[ExperimentOut]:
    rows = (await db.execute(select(Experiment))).scalars().all()
    if not rows:
        await AnalysisService(db).seed_experiments()
        await db.commit()
        rows = (await db.execute(select(Experiment))).scalars().all()
    return [ExperimentOut.model_validate(r) for r in rows]


@app.get("/experiments/{experiment_id}", response_model=ExperimentOut)
async def get_experiment(experiment_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ExperimentOut:
    row = await db.get(Experiment, experiment_id)
    if not row:
        raise HTTPException(404, "experiment not found")
    return ExperimentOut.model_validate(row)


@app.post("/analysis/recompute", response_model=RecomputeResult)
async def recompute(db: AsyncSession = Depends(get_db)) -> RecomputeResult:
    result = await AnalysisService(db, seed=settings.random_seed).recompute()
    return RecomputeResult(
        sessions_processed=result["sessions_processed"],
        clusters=result["clusters"],
        anomalies=result["anomalies"],
        model_run_ids=result["model_run_ids"],
    )


@app.get("/sessions/{session_id}/analysis", response_model=AnalysisSummary)
async def session_analysis(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> AnalysisSummary:
    svc = TelemetryService(db)
    session = await svc.get_session(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    analysis = AnalysisService(db)
    text = analysis.analyst_summary(session, session.features, session.anomaly, session.actor_label_row)
    label = session.actor_label_row
    return AnalysisSummary(
        session_id=session.id,
        summary=text,
        experimental_classification=label.label if label else (session.actor_label or "UNKNOWN"),
        confidence=label.confidence if label else 0.0,
        caveats="Experimental and probabilistic; not definitive AI attribution.",
    )


@app.post("/ingest/artifact")
async def ingest_artifact_interaction(
    session_id: uuid.UUID,
    artifact_name: str,
    subsequent_actions: list[str] | None = None,
    time_to_next_action_ms: int | None = None,
    influenced_navigation: bool = False,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    art = (
        await db.execute(select(DeceptionArtifact).where(DeceptionArtifact.name == artifact_name))
    ).scalar_one_or_none()
    if not art:
        raise HTTPException(404, "artifact not found")
    db.add(
        DeceptionInteraction(
            session_id=session_id,
            artifact_id=art.id,
            subsequent_actions=subsequent_actions or [],
            time_to_next_action_ms=time_to_next_action_ms,
            influenced_navigation=influenced_navigation,
        )
    )
    await db.commit()
    return {"status": "ok"}
