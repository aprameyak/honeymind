# HoneyMind

Lab for adaptive honeypots and attacker-session analysis (human, scripted, and simulated LLM actors).

Actor-class labels from the ML stack are experimental. Do not treat them as proof that a live internet host is AI-driven.

## Architecture

[`ARCHITECTURE.md`](./ARCHITECTURE.md)

```text
Simulated Actors → Deception Gateway → SSH/HTTP/API Honeypots
        → Event Pipeline → Session Engine → AI/ML Engine
        → Deception Policy → Analytics API → Dashboard
```

## Threat model

| Assumption | Implication |
|------------|-------------|
| Traffic to honeypots is hostile | Validate, rate-limit |
| Attacker text may be injection | Delimit/sanitize; never feed into privileged prompts |
| Containers may be probed | No privileged mode, no Docker socket, no host network, drop caps |
| LLM output is untrusted | Validate structure; no shell/FS/network tools for the model |

[`infrastructure/THREAT_MODEL.md`](./infrastructure/THREAT_MODEL.md)

## Containment

- Docker Compose lab networks only
- Honeypots: read-only root, tmpfs `/tmp`, resource limits, `no-new-privileges`, dropped capabilities
- Fake org **Nectar Analytics LLC** (all credentials/hosts are synthetic)
- Simulated actors allowlisted to lab hostnames
- LLM off by default (`LLM_PROVIDER=none`)

## Stack

Next.js / TypeScript / Tailwind / Recharts · FastAPI / SQLAlchemy / Alembic · PostgreSQL · scikit-learn · Docker Compose

## Install

```bash
git clone https://github.com/aprameyak/honeymind.git
cd honeymind
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3001 |
| API | http://localhost:8000/docs |
| SSH emulator | http://localhost:2222 |
| HTTP honeypot | http://localhost:8080 |
| Fake API | http://localhost:8081 |

`curl http://localhost:8000/health`

## Simulated traffic

```bash
docker compose --profile actors run --rm actors
```

Or:

```bash
pip install httpx
SSH_HOST=localhost SSH_PORT=2222 HTTP_URL=http://localhost:8080 API_URL=http://localhost:8081 \
  python -m actors.run_all
curl -X POST http://localhost:8000/analysis/recompute
```

## ML pipeline

1. Normalize events → actions + session text
2. Behavioral features
3. Session embedding (default: deterministic hash embedding)
4. Hybrid vector = embedding ⊕ features
5. DBSCAN clustering
6. Isolation Forest anomaly scores
7. Experimental actor-class likelihoods

Runs store algorithm, version, params, and seed.

## Evaluation

Research questions RQ1–RQ5 are in `ARCHITECTURE.md`.

```bash
cd backend && pip install -r requirements.txt
cd .. && PYTHONPATH=backend python scripts/run_evaluation.py
```

Output: `datasets/evaluation_report.json`

## API

OpenAPI: http://localhost:8000/docs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/sessions` | List sessions |
| GET | `/sessions/{id}` | Detail |
| GET | `/sessions/{id}/events` | Timeline |
| GET | `/analytics/overview` | KPIs |
| GET | `/analytics/clusters` | Clusters |
| GET | `/analytics/anomalies` | Anomalies |
| GET | `/experiments` | Deception experiments |
| POST | `/analysis/recompute` | Rebuild features/ML |
| POST | `/ingest/events` | Telemetry (optional `x-ingest-token` if `INGEST_TOKEN` set) |
| POST | `/deception/respond` | Synthetic responses |

Dashboard pages live at http://localhost:3001

## Limits

- SSH path is an HTTP-emulated shell (not full Cowrie)
- Default embeddings are hash-based
- Adaptive deception is rule-based (no RL)
- Actor classification is experimental
- Not for internet exposure

## Tests

```bash
cd backend && pip install -r requirements.txt && pip install pyyaml aiosqlite
cd .. && PYTHONPATH=backend:tests:. pytest tests/ -q
```

## License

MIT. Lab use only on networks you own or have permission to run.
