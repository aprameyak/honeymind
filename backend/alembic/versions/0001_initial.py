"""Initial HoneyMind schema."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("component", sa.String(64), nullable=False),
        sa.Column("algorithm", sa.String(64), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("random_seed", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
    )
    op.create_table(
        "experiments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("expected_observations", sa.JSON(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "clusters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_run_id", sa.String(36), sa.ForeignKey("model_runs.id"), nullable=False),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("common_behaviors", sa.JSON(), nullable=False),
        sa.Column("representative_session_ids", sa.JSON(), nullable=False),
        sa.Column("centroid", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("service", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actor_label", sa.String(32), nullable=True),
        sa.Column("cluster_id", sa.String(36), sa.ForeignKey("clusters.id"), nullable=True),
        sa.Column("deception_mode", sa.String(16), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("service", sa.String(16), nullable=False),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("response_type", sa.String(32), nullable=False),
        sa.Column("response_preview", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("session_depth", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    op.create_index("ix_events_session_id", "events", ["session_id"])
    op.create_index("ix_events_timestamp", "events", ["timestamp"])
    op.create_table(
        "session_features",
        sa.Column("session_id", sa.String(36), sa.ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("feature_vector", sa.JSON(), nullable=False),
        sa.Column("normalized_vector", sa.JSON(), nullable=False),
        sa.Column("semantic_actions", sa.JSON(), nullable=False),
        sa.Column("session_summary", sa.Text(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_run_id", sa.String(36), sa.ForeignKey("model_runs.id"), nullable=True),
    )
    op.create_table(
        "session_embeddings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("vector", sa.JSON(), nullable=False),
        sa.Column("dim", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_session_embeddings_session_id", "session_embeddings", ["session_id"])
    op.create_table(
        "anomaly_scores",
        sa.Column("session_id", sa.String(36), sa.ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("model_run_id", sa.String(36), sa.ForeignKey("model_runs.id"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("is_anomaly", sa.Boolean(), nullable=False),
        sa.Column("feature_contributions", sa.JSON(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "deception_artifacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("artifact_type", sa.String(64), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("experiment_id", sa.String(36), sa.ForeignKey("experiments.id"), nullable=True),
    )
    op.create_table(
        "deception_interactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_id", sa.String(36), sa.ForeignKey("deception_artifacts.id"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("subsequent_actions", sa.JSON(), nullable=False),
        sa.Column("time_to_next_action_ms", sa.Integer(), nullable=True),
        sa.Column("influenced_navigation", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_deception_interactions_session_id", "deception_interactions", ["session_id"])
    op.create_table(
        "actor_labels",
        sa.Column("session_id", sa.String(36), sa.ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("label", sa.String(32), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("likelihoods", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "actor_labels",
        "deception_interactions",
        "deception_artifacts",
        "anomaly_scores",
        "session_embeddings",
        "session_features",
        "events",
        "sessions",
        "clusters",
        "experiments",
        "model_runs",
    ]:
        op.drop_table(table)
