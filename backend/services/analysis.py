from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.db import (
    Session,
    Event,
    SessionFeatures,
    SessionEmbedding,
    Cluster,
    AnomalyScore,
    ActorLabelRow,
    ModelRun,
    Experiment,
    DeceptionArtifact,
    DeceptionInteraction,
    utcnow,
)
from models.schemas import EventIngest
from ml.features.extractor import (
    extract_features,
    normalize_action,
    build_session_summary,
    normalize_features,
    vector_as_list,
    FEATURE_KEYS,
)
from ml.embeddings.service import EmbeddingService
from ml.clustering.service import ClusteringService
from ml.anomaly.detector import AnomalyDetector
from ml.classification.actor import ActorClassifier
from experiments.framework import ExperimentRegistry
import numpy as np


class TelemetryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ingest(self, payload: EventIngest) -> tuple[Session, Event]:
        session: Optional[Session] = None
        if payload.session_id:
            session = await self.db.get(Session, payload.session_id)
        if session is None:
            session = Session(
                id=payload.session_id or uuid.uuid4(),
                service=payload.service,
                actor_label=payload.actor_label,
                deception_mode=payload.deception_mode,
                metadata_json=payload.metadata or {},
            )
            self.db.add(session)
            await self.db.flush()

        ts = payload.timestamp or utcnow()
        event = Event(
            session_id=session.id,
            timestamp=ts,
            service=payload.service,
            action_type=payload.action_type,
            action=payload.action,
            response_type=payload.response_type,
            response_preview=(payload.response_preview or "")[:2000],
            latency_ms=payload.latency_ms,
            session_depth=payload.session_depth,
            metadata_json=payload.metadata or {},
        )
        self.db.add(event)
        session.ended_at = ts
        if payload.actor_label and not session.actor_label:
            session.actor_label = payload.actor_label
        await self.db.commit()
        await self.db.refresh(session)
        await self.db.refresh(event)
        return session, event

    async def list_sessions(self, limit: int = 100) -> list[Session]:
        result = await self.db.execute(
            select(Session).order_by(Session.started_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_session(self, session_id: uuid.UUID) -> Optional[Session]:
        result = await self.db.execute(
            select(Session)
            .options(selectinload(Session.events), selectinload(Session.features), selectinload(Session.anomaly), selectinload(Session.actor_label_row))
            .where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_events(self, session_id: uuid.UUID) -> list[Event]:
        result = await self.db.execute(
            select(Event).where(Event.session_id == session_id).order_by(Event.timestamp.asc())
        )
        return list(result.scalars().all())


class AnalysisService:
    def __init__(self, db: AsyncSession, seed: int = 42) -> None:
        self.db = db
        self.seed = seed
        self.embeddings = EmbeddingService()
        self.clustering = ClusteringService(eps=0.85, min_samples=2)
        self.anomaly = AnomalyDetector(random_seed=seed)
        self.classifier = ActorClassifier()
        self.experiments = ExperimentRegistry()

    async def recompute(self) -> dict[str, Any]:
        result = await self.db.execute(
            select(Session).options(selectinload(Session.events))
        )
        sessions = list(result.scalars().all())
        if not sessions:
            return {"sessions_processed": 0, "clusters": 0, "anomalies": 0, "model_run_ids": {}}

        feature_run = ModelRun(
            component="features",
            algorithm="behavioral_v1",
            version="1.0.0",
            params={"keys": FEATURE_KEYS},
            random_seed=self.seed,
            metrics={},
        )
        emb_run = ModelRun(
            component="embeddings",
            algorithm=self.embeddings.provider.model_name,
            version=self.embeddings.provider.model_version,
            params={"dim": self.embeddings.provider.dim},
            random_seed=self.seed,
            metrics={},
        )
        self.db.add_all([feature_run, emb_run])
        await self.db.flush()

        raw_vectors: list[dict[str, float]] = []
        semantic_all: list[list[str]] = []
        summaries: list[str] = []
        session_ids: list[str] = []

        for session in sessions:
            events = sorted(session.events, key=lambda e: e.timestamp)
            event_dicts = [
                {
                    "timestamp": e.timestamp,
                    "action": e.action,
                    "action_type": e.action_type,
                    "session_depth": e.session_depth,
                }
                for e in events
            ]
            feats = extract_features(event_dicts)
            semantic = [normalize_action(e.action, e.action_type) for e in events]
            summary = build_session_summary(semantic, session.service)
            raw_vectors.append(feats)
            semantic_all.append(semantic)
            summaries.append(summary)
            session_ids.append(str(session.id))

        normalized = normalize_features(raw_vectors)

        await self.db.execute(delete(SessionFeatures))
        await self.db.execute(delete(SessionEmbedding))

        hybrid_matrix = []
        behavioral_matrix = []
        for i, session in enumerate(sessions):
            sf = SessionFeatures(
                session_id=session.id,
                feature_vector=raw_vectors[i],
                normalized_vector=normalized[i],
                semantic_actions=semantic_all[i],
                session_summary=summaries[i],
                model_run_id=feature_run.id,
            )
            self.db.add(sf)
            emb = self.embeddings.embed_session(summaries[i])
            self.db.add(
                SessionEmbedding(
                    session_id=session.id,
                    kind="session",
                    vector=emb,
                    dim=len(emb),
                    model_name=self.embeddings.provider.model_name,
                    model_version=self.embeddings.provider.model_version,
                )
            )
            bvec = vector_as_list(normalized[i])
            behavioral_matrix.append(bvec)
            hybrid_matrix.append(self.embeddings.hybrid(emb, bvec))

            classification = self.classifier.classify(raw_vectors[i], semantic_all[i])
            existing = await self.db.get(ActorLabelRow, session.id)
            if existing:
                await self.db.delete(existing)
                await self.db.flush()
            source = "ground_truth" if session.actor_label else "experimental"
            label = session.actor_label or classification.label
            self.db.add(
                ActorLabelRow(
                    session_id=session.id,
                    label=label,
                    source=source,
                    likelihoods=classification.likelihoods,
                    evidence=classification.evidence,
                    confidence=classification.confidence if not session.actor_label else 1.0,
                )
            )

        X = np.array(hybrid_matrix, dtype=np.float64)
        B = np.array(behavioral_matrix, dtype=np.float64)

        cluster_run = ModelRun(
            component="clustering",
            algorithm="dbscan",
            version="1.0.0",
            params={"eps": 0.85, "min_samples": 2},
            random_seed=self.seed,
            metrics={},
        )
        self.db.add(cluster_run)
        await self.db.flush()

        for session in sessions:
            session.cluster_id = None
        await self.db.flush()
        await self.db.execute(delete(Cluster))
        cluster_result = self.clustering.fit_predict(X, session_ids, semantic_all)
        cluster_id_by_external: dict[int, uuid.UUID] = {}
        for c in cluster_result.clusters:
            row = Cluster(
                model_run_id=cluster_run.id,
                external_id=c["external_id"],
                size=c["size"],
                common_behaviors=c["common_behaviors"],
                representative_session_ids=c["representative_session_ids"],
                centroid=c["centroid"],
            )
            self.db.add(row)
            await self.db.flush()
            cluster_id_by_external[c["external_id"]] = row.id

        for i, session in enumerate(sessions):
            lab = cluster_result.labels[i]
            session.cluster_id = cluster_id_by_external.get(lab)

        anomaly_run = ModelRun(
            component="anomaly",
            algorithm="isolation_forest",
            version="1.0.0",
            params={"contamination": 0.15},
            random_seed=self.seed,
            metrics={},
        )
        self.db.add(anomaly_run)
        await self.db.flush()

        await self.db.execute(delete(AnomalyScore))
        self.anomaly.fit(B)
        anomaly_result = self.anomaly.score_many(B)
        anom_count = 0
        for i, session in enumerate(sessions):
            self.db.add(
                AnomalyScore(
                    session_id=session.id,
                    model_run_id=anomaly_run.id,
                    score=anomaly_result.scores[i],
                    is_anomaly=anomaly_result.is_anomaly[i],
                    feature_contributions=anomaly_result.contributions[i],
                )
            )
            if anomaly_result.is_anomaly[i]:
                anom_count += 1

        await self.seed_experiments()
        await self.db.commit()
        return {
            "sessions_processed": len(sessions),
            "clusters": len([c for c in cluster_result.clusters if c["external_id"] != -1]),
            "anomalies": anom_count,
            "model_run_ids": {
                "features": str(feature_run.id),
                "embeddings": str(emb_run.id),
                "clustering": str(cluster_run.id),
                "anomaly": str(anomaly_run.id),
            },
            "pca_coords": [
                {"session_id": session_ids[i], "x": cluster_result.coords_2d[i][0], "y": cluster_result.coords_2d[i][1], "cluster": cluster_result.labels[i]}
                for i in range(len(session_ids))
            ],
        }

    async def seed_experiments(self) -> None:
        for exp in self.experiments.enabled():
            existing = await self.db.execute(select(Experiment).where(Experiment.name == exp.name))
            row = existing.scalar_one_or_none()
            if row is None:
                row = Experiment(
                    id=uuid.UUID(exp.experiment_id) if len(exp.experiment_id) == 36 else uuid.uuid4(),
                    name=exp.name,
                    description=f"Deception experiment: {exp.name}",
                    enabled=exp.enabled,
                    expected_observations=exp.expected_observations,
                    config=exp.artifact,
                )
                self.db.add(row)
                await self.db.flush()
            art = await self.db.execute(
                select(DeceptionArtifact).where(DeceptionArtifact.name == exp.name)
            )
            if art.scalar_one_or_none() is None:
                self.db.add(
                    DeceptionArtifact(
                        name=exp.name,
                        artifact_type=exp.artifact.get("type", "synthetic"),
                        content=exp.artifact,
                        enabled=exp.enabled,
                        experiment_id=row.id,
                    )
                )

    async def overview(self) -> dict[str, Any]:
        total_sessions = await self.db.scalar(select(func.count()).select_from(Session)) or 0
        total_events = await self.db.scalar(select(func.count()).select_from(Event)) or 0
        anomalies = await self.db.scalar(
            select(func.count()).select_from(AnomalyScore).where(AnomalyScore.is_anomaly.is_(True))
        ) or 0
        clusters = await self.db.scalar(
            select(func.count()).select_from(Cluster).where(Cluster.external_id != -1)
        ) or 0

        sessions = (await self.db.execute(select(Session))).scalars().all()
        service_dist: dict[str, int] = {}
        by_day: dict[str, int] = {}
        actor_class: dict[str, int] = {}
        for s in sessions:
            service_dist[s.service] = service_dist.get(s.service, 0) + 1
            day = s.started_at.strftime("%Y-%m-%d")
            by_day[day] = by_day.get(day, 0) + 1
            label = s.actor_label or "UNKNOWN"
            actor_class[label] = actor_class.get(label, 0) + 1

        labels = (await self.db.execute(select(ActorLabelRow))).scalars().all()
        if labels:
            actor_class = {}
            for lab in labels:
                actor_class[lab.label] = actor_class.get(lab.label, 0) + 1

        return {
            "total_sessions": total_sessions,
            "total_events": total_events,
            "anomalies_detected": anomalies,
            "cluster_count": clusters,
            "sessions_over_time": [{"date": k, "count": v} for k, v in sorted(by_day.items())],
            "service_distribution": service_dist,
            "actor_classifications": actor_class,
        }

    def analyst_summary(self, session: Session, features: SessionFeatures | None, anomaly: AnomalyScore | None, label: ActorLabelRow | None) -> str:
        parts = []
        semantic = features.semantic_actions if features else []
        if "SYSTEM_DISCOVERY" in semantic:
            parts.append("The session primarily consisted of systematic environment discovery.")
        if "DIRECTORY_ENUMERATION" in semantic and "CONFIG_DISCOVERY" in semantic:
            parts.append(
                "The actor progressed from host identification to filesystem enumeration and application configuration discovery."
            )
        if features and features.feature_vector.get("unique_command_ratio", 0) > 0.6:
            parts.append(
                "Behavior differs from the dominant scanner cluster because the actor reacted contextually to previous responses."
            )
        if anomaly and anomaly.is_anomaly:
            parts.append("The session received a high anomaly score.")
        cls = label.label if label else "UNKNOWN"
        conf = label.confidence if label else 0.0
        parts.append(f"Experimental classification: {cls} (confidence={conf:.2f}).")
        parts.append("Confidence is limited; classification should not be treated as definitive.")
        return " ".join(parts) if parts else "Insufficient telemetry for analysis."
