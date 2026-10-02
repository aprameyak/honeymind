# HoneyMind Architecture

Lab for adaptive honeypots and attacker-session analysis. Isolated defensive lab use only.

## 1. System Components

| Component | Responsibility |
|-----------|----------------|
| **Honeypot Layer** | Contained decoy services (SSH emulator, HTTP decoy, fake REST API); published lab ports |
| **Event Pipeline** | Normalizes raw interactions into typed telemetry events |
| **Session Engine** | Groups events into sessions; builds semantic action sequences and summaries |
| **EnvironmentState** | Maintains coherent fictional company/network world state |
| **DeceptionEngine** | Deterministic + optional LLM synthetic responses with strict validation |
| **DeceptionPolicy** | Rule-based adaptive strategy selection |
| **EmbeddingService** | Pluggable local embeddings for actions and sessions |
| **FeatureService** | Behavioral numerical feature vectors |
| **ClusteringService** | DBSCAN (optional HDBSCAN) unsupervised grouping |
| **AnomalyDetector** | Isolation Forest session scoring |
| **ActorClassifier** | Experimental HUMAN / SCRIPTED / LLM_AGENT / UNKNOWN likelihoods |
| **Experiment Framework** | Safe deception artifact A/B measurement |
| **Analytics API** | FastAPI REST surface; rate limits and optional ingest token |
| **Dashboard** | Next.js analytics UI |
| **Simulated Actors** | Allowlisted lab-only scripted / LLM research agents |

```
SIMULATED ACTORS (Human | Scripted | LLM Agent)
        │
        ▼
 SSH / HTTP / Fake API honeypots
        │
        ▼
 EVENT PIPELINE ──► SESSION ENGINE ──► Raw + Features + Embeddings
        │
        ▼
 AI/ML ENGINE (Clustering | Anomaly | Classification)
        │
        ▼
 DECEPTION ENGINE + POLICY ──► adaptive honeypot responses
        │
        ▼
 ANALYTICS API ──► DASHBOARD
```

## 2. Threat Model

**Assets to protect**
- Host filesystem, Docker socket, real credentials, cloud keys, production networks
- Analyst workstation integrity and outbound Internet from honeypot containers
- LLM provider keys (if configured) and prompt integrity

**Adversaries (assumed)**
- Anything interacting with honeypots is hostile
- Prompt-injection via attacker-controlled text
- Lateral movement attempts from compromised decoy containers
- Container escape / resource exhaustion

**Out of scope**
- Defending against physical host compromise
- Real Internet-facing deployment (lab-only by design)
- Attribution of real-world Internet actors as AI-generated

**Trust boundaries**
1. Host OS ↔ Docker bridge (honeypots never get host mounts / privileged / host network)
2. Honeypot network ↔ Backend (honeypots POST ingest; optional `x-ingest-token`)
3. Attacker input ↔ LLM system prompt (never concatenate untrusted text into privileged instructions)
4. LLM output ↔ honeypot response (structured validation before expose)

## 3. Containment Boundaries

- No privileged containers; no Docker socket mounts
- No host networking; `honeypot_net` is `internal: true` (no Internet egress from honeypots)
- Read-only root filesystems where practical; tmpfs for writable scratch
- CPU / memory / PID limits on all honeypot services
- Synthetic secrets only; env validation rejects real-looking production keys at startup
- Rate limiting and request body size limits on the analytics API
- Simulated actors allowlist: `honeypot-ssh`, `honeypot-http`, `honeypot-api`, `backend`, `localhost`, `127.0.0.1`
- LLM has **no tools** for shell, filesystem, Internet, or cloud APIs

## 4. Database Schema

### sessions
`id` UUID PK · `service` ENUM(ssh,http,api) · `started_at` · `ended_at` · `actor_label` nullable · `cluster_id` FK nullable · `deception_mode` (static|adaptive) · `metadata` JSONB

### events
`id` UUID PK · `session_id` FK · `timestamp` · `service` · `action_type` · `action` TEXT · `response_type` · `response_preview` · `latency_ms` · `session_depth` INT · `metadata` JSONB

### session_features
`session_id` PK/FK · `feature_vector` JSONB · `normalized_vector` JSONB · `semantic_actions` TEXT[] · `session_summary` TEXT · `computed_at` · `model_run_id` FK

### session_embeddings
`id` UUID PK · `session_id` FK · `kind` (action|sequence|session) · `vector` FLOAT[] · `dim` INT · `model_name` · `model_version` · `created_at`

### clusters
`id` UUID PK · `model_run_id` FK · `external_id` INT · `size` INT · `common_behaviors` JSONB · `representative_session_ids` UUID[] · `centroid` FLOAT[] nullable

### anomaly_scores
`session_id` PK/FK · `model_run_id` FK · `score` FLOAT · `is_anomaly` BOOL · `feature_contributions` JSONB · `computed_at`

### deception_artifacts
`id` UUID PK · `name` · `artifact_type` · `content` JSONB · `enabled` BOOL · `experiment_id` FK nullable

### deception_interactions
`id` UUID PK · `session_id` FK · `artifact_id` FK · `timestamp` · `subsequent_actions` JSONB · `time_to_next_action_ms` · `influenced_navigation` BOOL

### experiments
`id` UUID PK · `name` · `description` · `enabled` · `expected_observations` JSONB · `config` JSONB · `created_at`

### actor_labels
`session_id` PK/FK · `label` ENUM(HUMAN,SCRIPTED_AUTOMATION,SIMULATED_LLM_AGENT,UNKNOWN) · `source` (ground_truth|experimental) · `likelihoods` JSONB · `evidence` JSONB · `confidence` FLOAT

### model_runs
`id` UUID PK · `component` · `algorithm` · `version` · `params` JSONB · `random_seed` INT · `created_at` · `metrics` JSONB

## 5. Event Schema

```json
{
  "session_id": "uuid",
  "timestamp": "ISO-8601",
  "service": "ssh|http|api",
  "action_type": "auth|command|http_request|api_call|artifact_access",
  "action": "string",
  "response_type": "deterministic|generated|static|error",
  "latency_ms": 0,
  "session_depth": 0,
  "metadata": {}
}
```

## 6. Session Feature Schema

```json
{
  "session_duration": 0.0,
  "command_count": 0,
  "mean_interaction_delay": 0.0,
  "interaction_delay_variance": 0.0,
  "unique_command_ratio": 0.0,
  "repeated_command_ratio": 0.0,
  "reconnaissance_ratio": 0.0,
  "filesystem_access_ratio": 0.0,
  "deception_interaction_count": 0,
  "session_depth": 0,
  "auth_attempt_count": 0,
  "unique_resources": 0
}
```

Hybrid representation = `normalize(behavioral_vector) ⊕ session_embedding[:k]` (configurable).

## 7. MVP Acceptance Criteria

1. `docker compose up` starts Postgres, backend, frontend, three honeypots
2. Simulated actors generate labeled sessions into the DB
3. Dashboard shows overview, live sessions, session explorer, clusters, anomalies, experiments
4. `POST /analysis/recompute` runs features + embeddings + DBSCAN + Isolation Forest
5. Containment: honeypot services lack Docker socket, privileged mode, host network
6. Unit + API + feature + containment tests pass
7. No real secrets committed; `.env.example` documents all vars
8. Adaptive vs static evaluation script produces metrics JSON

## 8. Repository Structure

```
honeymind/
├── ARCHITECTURE.md
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── frontend/                 # Next.js dashboard
├── backend/                  # FastAPI + ML + deception
│   ├── api/
│   ├── models/
│   ├── services/
│   ├── ml/
│   ├── deception/
│   ├── experiments/
│   └── alembic/
├── honeypots/{ssh,http,api}/
├── actors/{scripted,llm}/
├── infrastructure/
├── datasets/
├── scripts/
└── tests/
```

## 9. Research Questions

- **RQ1** Semantic+behavioral distinguish LLM agents vs automation?
- **RQ2** Adaptive honeypots increase engagement vs static?
- **RQ3** Which signals best identify agent-like behavior?
- **RQ4** How do actor classes react to deception artifacts?
- **RQ5** Hybrid embedding+features beat either alone?
