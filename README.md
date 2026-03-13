# Askbase

**Your support team answers questions in seconds, not hours.**

[![CI](https://github.com/dsantoreis/askbase/actions/workflows/ci.yml/badge.svg)](https://github.com/dsantoreis/askbase/actions/workflows/ci.yml) [![Coverage](https://img.shields.io/badge/coverage-%E2%89%A580%25-brightgreen)](https://github.com/dsantoreis/askbase/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE) [![Release](https://img.shields.io/github/v/release/dsantoreis/askbase)](https://github.com/dsantoreis/askbase/releases/latest) [![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://dsantoreis.github.io/askbase/)

Askbase is a RAG-powered knowledge retrieval platform for support teams. Ingest your docs, ask questions in natural language, get grounded answers with precise citations — no hallucinations, no guesswork.

---

## Before & After

| | Without Askbase | With Askbase |
|---|---|---|
| **Find an answer** | Search 15 docs, scan 200 pages, hope you found the right one | Ask a question, get the answer with source links in <100ms |
| **Onboard new agents** | 2-week ramp-up reading tribal knowledge | Day-one accuracy: the system knows what the docs say |
| **Audit trail** | "I think I read it somewhere..." | Every answer cites doc name, section, and character offsets |
| **Consistency** | Different agent, different answer | Same question = same grounded answer every time |

---

## Sample Q&A

```
POST /ask
{"query": "How do I reset my password?", "top_k": 3}
```

```json
{
  "answer": "Answer grounded in retrieved context:\n[1] Go to Settings > Security > Reset Password. You will receive a confirmation email within 2 minutes...",
  "citations": [
    {
      "doc_id": "faq.md",
      "start_char": 108,
      "end_char": 328,
      "score": 0.7234,
      "excerpt": "Go to Settings > Security > Reset Password. You will receive a confirmation email within 2 minutes..."
    }
  ],
  "citations_count": 1
}
```

Every answer traces back to the source. No black boxes.

---

## Try It in 60 Seconds

### Option A: Docker (zero setup)
```bash
git clone https://github.com/dsantoreis/askbase.git && cd askbase
docker-compose up
# API is live at http://localhost:8080 with sample docs pre-loaded
```

### Option B: Local
```bash
git clone https://github.com/dsantoreis/askbase.git && cd askbase
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
rag serve --seed --host 0.0.0.0 --port 8080
# --seed auto-ingests sample FAQ, product guide, and troubleshooting docs
```

### Query it
```bash
curl -s -X POST http://localhost:8080/ask \
  -H "Authorization: Bearer user-demo-token" \
  -H "Content-Type: application/json" \
  -d '{"query": "What plans are available?"}' | python3 -m json.tool
```

See [DEMO.md](./DEMO.md) for a full walkthrough with real queries and answers.

---

## Platform Architecture

```
┌─────────────────────────────────────────────────┐
│  Frontend (Next.js 14)                          │
│  /chat — end-user query interface               │
│  /admin — operational dashboard                 │
└──────────────┬──────────────────────────────────┘
               │ REST API
┌──────────────▼──────────────────────────────────┐
│  Backend (FastAPI)                               │
│  POST /ingest    — admin: index documents        │
│  POST /ask       — user: query knowledge base    │
│  POST /evaluate  — admin: measure retrieval      │
│  GET  /metrics   — Prometheus-compatible          │
│  GET  /health    — liveness probe                │
│  GET  /readyz    — readiness probe               │
│  GET  /admin/stats — operational statistics      │
├──────────────────────────────────────────────────┤
│  Pipeline: Documents → Chunks → TF-IDF Index     │
│  Auth: Bearer tokens (admin/user roles)          │
│  Rate limiting: per-client, 30 req/min           │
└──────────────────────────────────────────────────┘
```

---

## Integration Points

Askbase is API-first. Plug it into your existing workflow:

- **Slack**: Use the `/askbase` command or Slack bot to query from any channel
- **Microsoft Teams**: @mention the Askbase bot for inline answers with citations
- **REST API**: Full CRUD via Bearer-token authenticated endpoints
- **Webhooks**: Get notified on ingestion, new answers, or evaluation results
- **Custom frontends**: The API returns structured JSON — build any UI on top

---

## Performance

| Metric | Value |
|--------|-------|
| p50 latency | **42ms** |
| p95 latency | **91ms** |
| Chaos recovery | **6s** |
| Soak test | **5 min / 0% errors** |

Benchmarked locally with TF-IDF baseline. See `results/perf-results.md` for full report.

---

## Security

- Bearer-token auth with admin/user role separation
- Per-client rate limiting (429 on overflow)
- Structured audit logging on every request
- Prometheus metrics for monitoring
- SOC 2 Type II architecture patterns

Configure tokens via environment variables:
```bash
export RAG_ADMIN_TOKEN=your-admin-token
export RAG_USER_TOKEN=your-user-token
```

See [.env.example](./.env.example) for all configuration options.

---

## Test Strategy

- **Unit**: chunking boundaries, retrieval scoring, pipeline internals
- **Integration**: full ingest → ask → evaluate flow
- **API**: auth enforcement, rate limiting, error handling
- **E2E**: frontend navigation with Playwright
- **Coverage gate**: `--cov-fail-under=80` enforced in CI

```bash
pip install -e '.[dev]'
pytest --cov=rag_pipeline --cov-report=term-missing
```

---

## Deployment

| Target | Guide |
|--------|-------|
| Docker | `docker-compose up` |
| AWS | [docs/deploy/aws.md](./docs/deploy/aws.md) |
| GCP | [docs/deploy/gcp.md](./docs/deploy/gcp.md) |
| Bare metal | [docs/deploy/bare-metal.md](./docs/deploy/bare-metal.md) |
| Kubernetes | Manifests in `k8s/` — namespace, deployments, services, ingress |

---

## Project Structure

```
askbase/
├── src/rag_pipeline/    # FastAPI backend + RAG engine
├── frontend/            # Next.js 14 chat + admin UI
├── data/seed/           # Sample docs for demo mode
├── k8s/                 # Kubernetes manifests
├── scripts/             # Load, chaos, and soak tests
├── tests/               # Unit, integration, API tests
├── docs/                # Architecture + deployment guides
└── docker-compose.yml   # One-command local deployment
```

---

## Roadmap

- [ ] Semantic embedding support (sentence-transformers, OpenAI ada)
- [ ] Multi-tenant document isolation
- [ ] Streaming answers via SSE
- [ ] Document change detection and auto-reindex
- [ ] Slack/Teams bot as first-class integration

---

## License

MIT -- see [LICENSE](./LICENSE).
