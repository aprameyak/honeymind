from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    pass


class GUID(TypeDecorator):
    """Platform-independent UUID type."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(str(value))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ServiceType(str, Enum):
    SSH = "ssh"
    HTTP = "http"
    API = "api"


class ActorLabel(str, Enum):
    HUMAN = "HUMAN"
    SCRIPTED_AUTOMATION = "SCRIPTED_AUTOMATION"
    SIMULATED_LLM_AGENT = "SIMULATED_LLM_AGENT"
    UNKNOWN = "UNKNOWN"


class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    component: Mapped[str] = mapped_column(String(64))
    algorithm: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    random_seed: Mapped[int] = mapped_column(Integer, default=42)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    expected_observations: Mapped[dict] = mapped_column(JSON, default=dict)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    artifacts: Mapped[list["DeceptionArtifact"]] = relationship(back_populates="experiment")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    service: Mapped[str] = mapped_column(String(16))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actor_label: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    cluster_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("clusters.id"), nullable=True)
    deception_mode: Mapped[str] = mapped_column(String(16), default="adaptive")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    events: Mapped[list["Event"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    features: Mapped[Optional["SessionFeatures"]] = relationship(back_populates="session", uselist=False)
    embeddings: Mapped[list["SessionEmbedding"]] = relationship(back_populates="session")
    anomaly: Mapped[Optional["AnomalyScore"]] = relationship(back_populates="session", uselist=False)
    actor_label_row: Mapped[Optional["ActorLabelRow"]] = relationship(back_populates="session", uselist=False)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    service: Mapped[str] = mapped_column(String(16))
    action_type: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(Text)
    response_type: Mapped[str] = mapped_column(String(32), default="deterministic")
    response_preview: Mapped[str] = mapped_column(Text, default="")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    session_depth: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    session: Mapped["Session"] = relationship(back_populates="events")


class SessionFeatures(Base):
    __tablename__ = "session_features"

    session_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    feature_vector: Mapped[dict] = mapped_column(JSON, default=dict)
    normalized_vector: Mapped[dict] = mapped_column(JSON, default=dict)
    semantic_actions: Mapped[list] = mapped_column(JSON, default=list)
    session_summary: Mapped[str] = mapped_column(Text, default="")
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    model_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("model_runs.id"), nullable=True)

    session: Mapped["Session"] = relationship(back_populates="features")


class SessionEmbedding(Base):
    __tablename__ = "session_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="session")
    vector: Mapped[list] = mapped_column(JSON, default=list)
    dim: Mapped[int] = mapped_column(Integer, default=0)
    model_name: Mapped[str] = mapped_column(String(64), default="hash")
    model_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped["Session"] = relationship(back_populates="embeddings")


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    model_run_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("model_runs.id"))
    external_id: Mapped[int] = mapped_column(Integer)
    size: Mapped[int] = mapped_column(Integer, default=0)
    common_behaviors: Mapped[dict] = mapped_column(JSON, default=dict)
    representative_session_ids: Mapped[list] = mapped_column(JSON, default=list)
    centroid: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AnomalyScore(Base):
    __tablename__ = "anomaly_scores"

    session_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    model_run_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("model_runs.id"))
    score: Mapped[float] = mapped_column(Float)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    feature_contributions: Mapped[dict] = mapped_column(JSON, default=dict)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped["Session"] = relationship(back_populates="anomaly")


class DeceptionArtifact(Base):
    __tablename__ = "deception_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    artifact_type: Mapped[str] = mapped_column(String(64))
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    experiment_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("experiments.id"), nullable=True)

    experiment: Mapped[Optional["Experiment"]] = relationship(back_populates="artifacts")
    interactions: Mapped[list["DeceptionInteraction"]] = relationship(back_populates="artifact")


class DeceptionInteraction(Base):
    __tablename__ = "deception_interactions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    artifact_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("deception_artifacts.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    subsequent_actions: Mapped[list] = mapped_column(JSON, default=list)
    time_to_next_action_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    influenced_navigation: Mapped[bool] = mapped_column(Boolean, default=False)

    artifact: Mapped["DeceptionArtifact"] = relationship(back_populates="interactions")


class ActorLabelRow(Base):
    __tablename__ = "actor_labels"

    session_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    label: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    source: Mapped[str] = mapped_column(String(32), default="experimental")
    likelihoods: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    session: Mapped["Session"] = relationship(back_populates="actor_label_row")
