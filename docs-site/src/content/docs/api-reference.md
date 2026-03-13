---
title: API Reference
description: Complete HTTP API for Askbase - ingest, query, evaluate, and monitor.
---

All endpoints require Bearer token authentication unless noted otherwise.

## Authentication

Askbase uses token-based auth with two roles:

| Role | Token (default) | Access |
|------|-----------------|--------|
| `admin` | `admin-demo-token` | All endpoints |
| `user` | `user-demo-token` | `/ask`, `/health`, `/readyz` |

Override defaults with environment variables `RAG_ADMIN_TOKEN` and `RAG_USER_TOKEN`.

```bash
curl -H "Authorization: Bearer user-demo-token" http://localhost:8080/ask ...
```

Requests without a valid token get `401`. User-role requests to admin endpoints get `403`.

## Rate limiting

Built-in per-IP rate limiter. Every `/ask` response includes current limits:

```json
{
  "rate_limit": { "limit": 100, "remaining": 97 }
}
```

---

## Endpoints

### POST /ask

Query the knowledge base. Returns a grounded answer with citations.

**Request:**
```json
{
  "query": "How do I reset my password?",
  "top_k": 3
}
```

| Field | Type | Default | Range |
|-------|------|---------|-------|
| `query` | string (required) | - | min 1 char |
| `top_k` | int | 3 | 1-10 |

**Response (200):**
```json
{
  "answer": "Go to Settings > Security > Reset Password...",
  "citations": [
    {
      "doc_id": "faq.md",
      "start_char": 108,
      "end_char": 328,
      "score": 0.7234,
      "excerpt": "Go to Settings > Security > Reset Password..."
    }
  ],
  "citations_count": 1,
  "rate_limit": { "limit": 100, "remaining": 99 }
}
```

**Errors:** `400` if no index is loaded, `401` if unauthenticated.

---

### POST /ingest

Ingest documents into the vector index. Admin only.

**Request:**
```json
{
  "paths": ["docs/", "data/faq.md"]
}
```

**Response (200):**
```json
{
  "chunks_indexed": 47,
  "index_path": "artifacts/rag_index.pkl"
}
```

Accepts directories (recursively ingests `.txt`, `.md`, `.pdf`) and individual files.

---

### POST /evaluate

Run context precision evaluation against a labeled dataset. Admin only.

**Request:**
```json
{
  "dataset_path": "eval/golden_set.json",
  "k": 5
}
```

**Response:** Precision metrics for retrieval quality assessment.

---

### GET /health

Health check. No auth required.

```json
{ "status": "ok", "index_loaded": true }
```

### GET /readyz

Readiness probe for Kubernetes. Returns chunk count and index status.

```json
{
  "ready": true,
  "chunks_loaded": 47,
  "index_path": "artifacts/rag_index.pkl"
}
```

### GET /statusz

Detailed status with uptime.

```json
{
  "status": "ok",
  "ready": true,
  "chunks_loaded": 47,
  "uptime_sec": 3600,
  "version": "4.0.0"
}
```

### GET /metrics

Prometheus-compatible metrics endpoint for monitoring request latency, error rates, and throughput.

### GET /admin/stats

Index statistics. Admin only.

```json
{
  "chunks_loaded": 47,
  "index_path": "artifacts/rag_index.pkl"
}
```
