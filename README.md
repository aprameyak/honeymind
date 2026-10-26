# honeymind

A self-contained lab for defensive security research: decoy SSH, HTTP, and API services log every session, and a FastAPI backend groups, scores, and labels those sessions for review in a Next.js dashboard. Use it to study how different kinds of clients (human, scripted, agent-like) behave against honeypots, inside an isolated Docker network.

Actor-class labels are experimental and rule-based. They are not evidence that any real host is AI-driven, and the lab is not meant to be exposed to the internet.

## Quick start

Requires Docker with Compose.

```bash
git clone https://github.com/aprameyak/honeymind.git
cd honeymind
cp .env.example .env
docker compose up --build
```

The dashboard is at http://localhost:3001 and the API docs at http://localhost:8000/docs.

## Example

Send a command to the SSH emulator. The backend logs it as a session event and returns a deterministic response from the fictional environment:

```console
$ curl -s -X POST http://localhost:2222/exec -H 'Content-Type: application/json' \
    -d '{"session_id": "8f1c2a4e-0d3b-4f7a-9c11-2b6e5d7a9f00", "command": "uname"}'
{"output":"Linux web-01 5.15.0-synth #1 SMP x86_64 GNU/Linux","strategy":"deterministic","artifacts":[]}
```

Generate labeled traffic from the simulated actors, then rebuild clusters, anomaly scores, and labels:

```bash
docker compose --profile actors run --rm actors
curl -X POST http://localhost:8000/analysis/recompute
```

Results appear on the dashboard and through `GET /sessions`, `GET /analytics/clusters`, and `GET /analytics/anomalies`.

## Features

- Three decoy services in `honeypots/`: an HTTP-emulated SSH shell, an HTTP portal, and a fake internal REST API, all serving a fictional company ("Nectar Analytics") with synthetic credentials and hosts.
- Session analysis in `backend/ml/`: 12 behavioral features per session, a hybrid vector (hash embedding plus normalized features), scikit-learn DBSCAN clustering with a PCA 2D projection, and scikit-learn IsolationForest anomaly scores with per-feature contributions.
- Actor classification (HUMAN, SCRIPTED_AUTOMATION, SIMULATED_LLM_AGENT, UNKNOWN) using hand-written timing and behavior rules, with the triggered signals stored as evidence.
- A rule-based deception policy and deterministic response engine that decide which synthetic artifacts (fake configs, trap notes, inventory files) a session is shown.
- Simulated actors in `actors/` that generate labeled traffic and refuse to contact any host outside a lab allowlist.
- An offline evaluation script that compares static vs adaptive engagement, scores the classifier with precision/recall/F1, and compares behavioral, embedding, and hybrid representations.

## Tech stack

- Backend: Python 3.12, FastAPI, SQLAlchemy (async), Alembic, PostgreSQL 16
- Analysis: NumPy, scikit-learn (DBSCAN, IsolationForest, PCA, metrics)
- Honeypots and actors: FastAPI, httpx
- Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS, Recharts
- Docker Compose, GitHub Actions CI (pytest)

## Configuration, tests, and evaluation

Settings live in `.env` (copied from `.env.example`, which holds synthetic values only). Variables: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, `DATABASE_URL_SYNC`, `BACKEND_HOST`, `BACKEND_PORT`, `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, `EMBEDDING_MODEL`, `RANDOM_SEED`, `RATE_LIMIT_PER_MINUTE`, `MAX_REQUEST_BYTES`, `HONEYMIND_ENV`, `INGEST_TOKEN`, `CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`.

Published ports: dashboard 3001, API 8000, SSH emulator 2222, HTTP honeypot 8080, fake API 8081. The backend container runs `alembic upgrade head` before starting.

Tests need Python 3.12. They cover unit logic, containment checks on `docker-compose.yml`, and API routes against in-memory SQLite:

```bash
pip install -r backend/requirements.txt
PYTHONPATH=backend:tests:. pytest tests/ -q
```

The offline evaluation runs on the fixture sessions in `tests/fixtures/sessions.py` and writes `datasets/evaluation_report.json`:

```bash
python scripts/run_evaluation.py
```

## How it works

1. Honeypots (`honeypots/ssh/app.py`, `honeypots/http/app.py`, `honeypots/api/app.py`) post each interaction to `POST /ingest/events`, optionally with an `x-ingest-token` header. The SSH emulator asks `POST /deception/respond` for command output.
2. `backend/deception/policy.py` picks a strategy from simple rules over the session's features and actions. `backend/deception/engine.py` returns deterministic responses from a per-session fictional environment and strips prompt-injection patterns from input. The engine has an LLM hook, but no provider is wired up, so all responses are deterministic.
3. `POST /analysis/recompute` (`backend/services/analysis.py`) maps raw actions to semantic labels, extracts features (`backend/ml/features/extractor.py`), embeds a text summary with a SHA-256 feature-hashing embedding (`backend/ml/embeddings/service.py`, no neural model), then runs DBSCAN, IsolationForest, and the rule-based actor classifier. Each run records algorithm, version, params, and seed.
4. The dashboard (`frontend/src/app/`) shows an overview, live sessions, a session explorer, clusters, anomalies, experiments, and per-session analysis.
5. Actors (`actors/scripted/`, `actors/llm/research_agent.py`) replay fixed command lists with different pacing. The "LLM agent" actor follows a scripted plan; it does not call a model.

Containment details (internal honeypot network, read-only containers, dropped capabilities, resource limits) are in `docker-compose.yml`, `ARCHITECTURE.md`, and `infrastructure/THREAT_MODEL.md`.

## Project structure

```
backend/        FastAPI app, models, Alembic migrations
  api/          REST routes, rate limiting, ingest token check
  ml/           features, embeddings, clustering, anomaly, classification
  deception/    policy, response engine, fictional environment
  experiments/  deception experiments and evaluation metrics
  services/     telemetry ingest and analysis pipeline
honeypots/      ssh, http, api decoy services
actors/         allowlisted simulated clients
frontend/       Next.js dashboard
scripts/        run_evaluation.py
tests/          unit, containment, and API tests plus fixture sessions
datasets/       evaluation output
```

## Contributing

Open an issue or a focused pull request. Run `pytest` before submitting; CI runs the same suite on every push and PR. Keep all credentials and hosts synthetic, and keep actors restricted to the lab allowlist.

## License

MIT. See LICENSE.
