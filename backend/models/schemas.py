from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class EventIngest(BaseModel):
    session_id: Optional[UUID] = None
    service: str
    action_type: str
    action: str
    response_type: str = "deterministic"
    response_preview: str = ""
    latency_ms: int = 0
    session_depth: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor_label: Optional[str] = None
    deception_mode: str = "adaptive"
    timestamp: Optional[datetime] = None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    timestamp: datetime
    service: str
    action_type: str
    action: str
    response_type: str
    response_preview: str
    latency_ms: int
    session_depth: int
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service: str
    started_at: datetime
    ended_at: Optional[datetime]
    actor_label: Optional[str]
    cluster_id: Optional[UUID]
    deception_mode: str
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")
    event_count: int = 0
    anomaly_score: Optional[float] = None
    experimental_classification: Optional[str] = None
    confidence: Optional[float] = None


class SessionDetail(SessionOut):
    semantic_actions: list[str] = Field(default_factory=list)
    session_summary: str = ""
    feature_vector: dict[str, Any] = Field(default_factory=dict)
    artifacts_accessed: list[str] = Field(default_factory=list)


class OverviewOut(BaseModel):
    total_sessions: int
    total_events: int
    anomalies_detected: int
    cluster_count: int
    sessions_over_time: list[dict[str, Any]]
    service_distribution: dict[str, int]
    actor_classifications: dict[str, int]


class ClusterOut(BaseModel):
    id: UUID
    external_id: int
    size: int
    common_behaviors: dict[str, Any]
    representative_session_ids: list[UUID]
    distance_hint: Optional[float] = None


class AnomalyOut(BaseModel):
    session_id: UUID
    score: float
    is_anomaly: bool
    feature_contributions: dict[str, Any]
    service: Optional[str] = None
    actor_label: Optional[str] = None


class ExperimentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    enabled: bool
    expected_observations: dict[str, Any]
    config: dict[str, Any]


class DeceptionRequest(BaseModel):
    session_id: Optional[UUID] = None
    service: str
    command: str
    hostname: str = "web-01"
    history: list[dict[str, str]] = Field(default_factory=list)
    deception_mode: str = "adaptive"
    behavior_hints: dict[str, Any] = Field(default_factory=dict)


class DeceptionResponse(BaseModel):
    session_id: UUID
    response: str
    response_type: str
    strategy: str
    artifacts_exposed: list[str] = Field(default_factory=list)
    environment_facts: dict[str, Any] = Field(default_factory=dict)


class AnalysisSummary(BaseModel):
    session_id: UUID
    summary: str
    experimental_classification: str
    confidence: float
    caveats: str


class RecomputeResult(BaseModel):
    sessions_processed: int
    clusters: int
    anomalies: int
    model_run_ids: dict[str, str]
