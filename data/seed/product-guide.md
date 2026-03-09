# Askbase Product Guide

## Getting Started

Askbase is a knowledge retrieval platform that helps support teams find accurate answers instantly. Instead of searching through dozens of documents manually, your team asks a question and gets a grounded answer with citations pointing to the exact source.

### Core Workflow

1. **Ingest**: Upload your documents (product docs, FAQs, runbooks, policies). Askbase chunks and indexes them automatically.
2. **Ask**: Type a natural-language question. The retrieval engine finds the most relevant passages.
3. **Answer**: Get a grounded answer with numbered citations linking back to specific document sections.

## Document Ingestion

### Supported Formats
- Markdown (.md)
- Plain text (.txt)
- PDF (.pdf)

### How Ingestion Works
Documents are split into overlapping chunks using a sliding window algorithm. This ensures that no information is lost at chunk boundaries. Each chunk retains metadata about its source document, character offsets, and position — enabling precise citations.

### Best Practices
- Keep documents focused on one topic each
- Use descriptive filenames (e.g., `password-reset-guide.md` instead of `doc1.md`)
- Update and re-ingest when content changes
- Aim for documents between 500 and 5,000 words for optimal chunking

## Search & Retrieval

### How Search Works
Askbase uses TF-IDF vectorization with bigram support and cosine similarity ranking. When you ask a question, the engine:
1. Vectorizes your query using the same vocabulary as the indexed documents
2. Computes similarity scores against all chunks
3. Returns the top-k most relevant chunks, ranked by score

### Query Tips
- Be specific: "How do I reset my password?" works better than "password"
- Use the terms your documents use: if docs say "two-factor authentication", use that instead of "2FA"
- Adjust top_k (1-10) to control how many source passages are returned

## Administration

### Admin Dashboard
The admin panel at `/admin` shows operational statistics including total chunks indexed, index file path, and system health. Access requires an admin-level Bearer token.

### Evaluation
Run evaluation datasets against your index to measure retrieval quality. The evaluation endpoint computes context precision at k — the fraction of retrieved documents that are actually relevant to each query.

### Monitoring
- `/health` — basic liveness check
- `/readyz` — readiness probe (confirms index is loaded)
- `/metrics` — Prometheus-compatible metrics (request count, latency histograms)

## API Reference

### POST /ingest
Upload and index documents.
- Auth: Admin token required
- Body: `{"paths": ["./docs", "./guides"]}`
- Response: `{"chunks_indexed": 142, "index_path": "artifacts/rag_index.pkl"}`

### POST /ask
Query the knowledge base.
- Auth: User or Admin token
- Body: `{"query": "How do I reset my password?", "top_k": 3}`
- Response includes answer text, citations array, and rate limit info

### GET /admin/stats
View operational statistics.
- Auth: Admin token required
- Response: `{"chunks_loaded": 142, "index_path": "artifacts/rag_index.pkl"}`

### POST /evaluate
Run evaluation against a dataset.
- Auth: Admin token required
- Body: `{"dataset_path": "eval/golden.jsonl", "k": 3}`

## Deployment Options

### Local Development
Run the backend with `rag serve` and the frontend with `npm run dev` in the frontend directory.

### Docker
Use `docker-compose up` for a one-command local deployment. The compose file mounts your documents directory and persists the index.

### Kubernetes
Production manifests are provided for namespace, backend/frontend deployments, services, and ingress. Configure secrets for auth tokens and adjust resource limits for your workload.

## Security

### Authentication
All API endpoints require Bearer token authentication. Two token levels are supported:
- **Admin token**: Full access to all endpoints including ingestion and evaluation
- **User token**: Access to query endpoints only

### Rate Limiting
Built-in per-client rate limiting prevents abuse. Default: 30 requests per 60-second window. Exceeding the limit returns HTTP 429 with a Retry-After value.

### Data Protection
- All traffic encrypted via TLS
- Index files should be stored on encrypted volumes in production
- Tokens should be rotated regularly and stored in a secrets manager
