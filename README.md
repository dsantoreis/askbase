# Enterprise RAG Platform (Portfolio Demo)

[![CI](https://github.com/OWNER/rag-pipeline-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/rag-pipeline-demo/actions/workflows/ci.yml)

Production-shaped **Enterprise RAG Platform**: backend API + Next.js chat + admin panel + auth/rate-limit/logging/metrics + Kubernetes + CI + test pyramid + performance scripts.

## Why this matters (business ROI)

- **Faster support resolution**: grounded answers with citations reduce average handling time.
- **Lower compliance risk**: admin-only ingestion/evaluation, auditable logs, explicit tokens.
- **Scalable delivery**: k8s manifests and CI pipelines make handoff to platform teams easy.
- **Cost control**: deterministic TF-IDF baseline for cheap retrieval before LLM expansion.

### Benchmark snapshot (local baseline)
- p50 latency: **42ms**
- p95 latency: **91ms**
- chaos recovery: **6s**
- soak: **5 min / 0% errors**

See `results/perf-results.md`.

## Platform components

- **Backend (FastAPI)**
  - `/ask`, `/ingest`, `/evaluate`, `/admin/stats`, `/metrics`, `/health`
  - Bearer-token auth (admin/user)
  - In-memory per-client rate limiting (429 on overflow)
  - Prometheus metrics and structured request logging
- **Frontend (Next.js 14)**
  - `/chat` end-user query UI
  - `/admin` operational panel
- **Kubernetes**
  - namespace, backend/frontend deployments/services, ingress
- **CI**
  - backend lint/test/coverage/build/docker
  - frontend lint/test/build/e2e

## Quickstart

### Backend
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
rag ingest ./docs --index artifacts/rag_index.pkl
rag serve --host 0.0.0.0 --port 8080 --index artifacts/rag_index.pkl
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Security defaults

- `RAG_ADMIN_TOKEN` (default `admin-demo-token`)
- `RAG_USER_TOKEN` (default `user-demo-token`)

Send as `Authorization: Bearer <token>`.

## Test strategy

- Unit: chunking, retrieval, pipeline internals
- Integration: ingest/ask/evaluate flow
- API: authz, metrics, request flow
- E2E: frontend navigation with Playwright

Coverage gate enforced in CI: `--cov-fail-under=80`.

## Deployment guides

- AWS: `docs/deploy/aws.md`
- GCP: `docs/deploy/gcp.md`
- Bare metal: `docs/deploy/bare-metal.md`

## Load / Chaos / Soak

- `python scripts/load_test.py --n 100`
- `bash scripts/chaos_test.sh`
- `bash scripts/soak_test.sh 300`
