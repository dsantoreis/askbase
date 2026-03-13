---
title: Getting Started
description: Get Askbase running locally or in Docker in under 2 minutes.
---

## Prerequisites

- Python 3.11+
- pip or Docker

## Option A: Docker (recommended)

```bash
git clone https://github.com/dsantoreis/askbase.git && cd askbase
docker-compose up
```

The API starts at `http://localhost:8080` with sample docs pre-loaded via `--seed`.

## Option B: Local install

```bash
git clone https://github.com/dsantoreis/askbase.git && cd askbase
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
```

### Ingest documents

Drop your `.txt`, `.md`, or `.pdf` files into a folder and ingest them:

```bash
rag ingest docs/ data/seed/
```

This chunks, embeds (TF-IDF), and indexes everything into `artifacts/rag_index.pkl`.

### Start the server

```bash
rag serve --seed --host 0.0.0.0 --port 8080
```

`--seed` auto-ingests `data/seed/` on first run if no index exists yet.

### Ask a question

```bash
curl -s -X POST http://localhost:8080/ask \
  -H "Authorization: Bearer user-demo-token" \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I reset my password?"}' | python3 -m json.tool
```

You get a grounded answer with citations pointing to exact document locations.

## CLI commands

| Command | What it does |
|---------|-------------|
| `rag ingest <paths...>` | Chunk and index documents |
| `rag ask "<question>"` | Query the index from the terminal |
| `rag serve` | Start the FastAPI server |
| `rag evaluate --dataset eval.json` | Run context precision evaluation |
| `rag status` | Show index stats (chunk count, path) |

### CLI options

```bash
# Custom chunk size and overlap
rag ingest docs/ --chunk-size 300 --overlap 50

# JSON output for scripting
rag ask "What plans exist?" --json --top-k 5

# Custom index path
rag serve --index /data/production.pkl --port 9090
```

## Next steps

- [API Reference](/api-reference) for full endpoint docs
- [Architecture](/architecture) for how the pipeline works
- [Deployment](/deployment) for production setup with Kubernetes
