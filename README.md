# HoneyMind

**AI-Adaptive Honeypot and Autonomous Attacker Analysis Platform**

Isolated cyber-deception research lab for studying attacker behavior, adaptive decoys, and experimental differentiation of human, scripted, and simulated LLM-driven actors.

> AI-agent detection is **experimental and probabilistic**. Do not treat model output as definitive proof that an unknown Internet actor is AI-generated.

## 1. Motivation

Traditional honeypots are static. Modern adversaries — including automation and emerging autonomous agents — adapt quickly. HoneyMind explores whether semantic embeddings, behavioral features, clustering, and rule-based adaptive deception can:

- prolong engagement in controlled experiments,
- surface unusual session structure,
- support research into actor-class signals **without** attacking real infrastructure.

## 2. Architecture

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for component definitions, schemas, and the implementation checklist.

```text
Simulated Actors → Deception Gateway → SSH/HTTP/API Honeypots
        → Event Pipeline → Session Engine → AI/ML Engine
        → Deception Policy → Analytics API → Dashboard
```

## 3. Threat Model

| Assumption | Implication |
|------------|-------------|
| Anything talking to honeypots is hostile | Validate, rate-limit, never trust input |
| Attacker text may attempt prompt injection | Delimit untrusted blocks; sanitize; never concatenate into privileged instructions |
| Containers may be probed for escape | No privileged mode, no Docker socket, no host network, cap_drop ALL on honeypots |
| LLM output is untrusted | Structured validation before expose; no LLM tools for shell/Internet/FS |

Full notes: [`infrastructure/THREAT_MODEL.md`](./infrastructure/THREAT_MODEL.md).

## 4. Safety / Containment

- Docker Compose lab networks only
- Honeypots: read-only root, tmpfs `/tmp`, resource limits, `no-new-privileges`, dropped capabilities
- Synthetic company **Nectar Analytics LLC** — all credentials/hosts/docs are fake
- Simulated actors hard-allowlist lab hostnames only
- Optional LLM is off by default (`LLM_PROVIDER=none`)

## 5. Technology Stack

- **Frontend:** Next.js, TypeScript, Tailwind, Recharts
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic
- **DB:** PostgreSQL
- **ML:** scikit-learn (DBSCAN, Isolation Forest), local hash embeddings (replaceable)
- **Infra:** Docker Compose

## 6. Installation

```bash
git clone <repo-url> honeymind
cd honeymind
cp .env.example .env
```

Requirements: Docker + Docker Compose. No paid cloud required.

## 7. Running Locally

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3001 |
| API | http://localhost:8000/docs |
| SSH emulator | http://localhost:2222 |
| HTTP honeypot | http://localhost:8080 |
| Fake API | http://localhost:8081 |

Health: `curl http://localhost:8000/health`

> If port 3000 is free on your machine, you can change the frontend mapping in `docker-compose.yml` to `3000:3000`.

## 8. Generating Simulated Traffic

```bash
docker compose --profile actors run --rm actors
```

Or from the host (with services up):

```bash
pip install httpx
SSH_HOST=localhost SSH_PORT=2222 HTTP_URL=http://localhost:8080 API_URL=http://localhost:8081 \
  python -m actors.run_all
```

Then recompute analysis:

```bash
curl -X POST http://localhost:8000/analysis/recompute
```

## 9. ML Methodology

1. Normalize events → semantic actions + textual session summary  
2. Extract behavioral feature vector (timing, ratios, depth, deception hits)  
3. Embed session summary (pluggable provider; default deterministic hash embedding)  
4. Hybrid = embedding prefix ⊕ normalized behavioral vector  
5. DBSCAN clustering on hybrid space (no automatic malice labels)  
6. Isolation Forest on behavioral vectors → anomaly scores + feature contributions  
7. Experimental actor classifier → likelihoods with explicit caveats  

Model runs store algorithm, version, params, and random seed for reproducibility.

## 10. Experimental Methodology

Research questions RQ1–RQ5 are defined in `ARCHITECTURE.md`.

Offline evaluation:

```bash
cd backend && pip install -r requirements.txt
cd .. && PYTHONPATH=backend python scripts/run_evaluation.py
```

Outputs: `datasets/evaluation_report.json` (precision/recall/F1, confusion matrix, static vs adaptive engagement, hybrid separation).

## 11. API Documentation

Interactive OpenAPI: http://localhost:8000/docs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/sessions` | List sessions |
| GET | `/sessions/{id}` | Session detail |
| GET | `/sessions/{id}/events` | Timeline |
| GET | `/analytics/overview` | Dashboard KPIs |
| GET | `/analytics/clusters` | Cluster table |
| GET | `/analytics/anomalies` | Ranked anomalies |
| GET | `/experiments` | Deception experiments |
| POST | `/analysis/recompute` | Rebuild features/ML |
| POST | `/ingest/events` | Honeypot telemetry |
| POST | `/deception/respond` | Synthetic response generation |

## 12. Dashboard

Pages: Overview · Live Sessions · Session Explorer · Clusters · Anomalies · Experiments · AI Analysis

Screenshots: run the stack and capture from http://localhost:3000 (placeholders until first local run).

## 13. Current Limitations

- SSH path is an HTTP-emulated shell protocol for lab safety (not a full Cowrie drop-in yet)
- Default embeddings are hash-based for offline determinism; swap in sentence-transformers when desired
- Adaptive deception is rule-based only (no RL)
- Actor classification is experimental
- Not for Internet exposure

## 14. Research Questions

- **RQ1** Distinguish simulated LLM agents from automation via semantic+behavioral reps?
- **RQ2** Do adaptive honeypots sustain longer engagement than static ones?
- **RQ3** Which behavioral signals best indicate agent-like behavior?
- **RQ4** How do actor classes react to deceptive artifacts?
- **RQ5** Does hybrid embedding+features beat either alone?

## 15. Future Work

- Cowrie integration behind the same ingest contract
- Optional local sentence-transformers / HDBSCAN
- Contextual bandits using collected policy decision logs
- Prometheus/Grafana exporters
- Richer PCA/UMAP cluster canvas in the UI

## Development & Tests

```bash
cd backend && pip install -r requirements.txt && pip install pyyaml aiosqlite
cd .. && PYTHONPATH=backend:tests:. pytest tests/ -q
```

Phase checklist lives in `ARCHITECTURE.md`.

## License

Research / educational lab software. Use only in isolated environments you own or have permission to operate.
