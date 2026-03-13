---
title: Deployment
description: Run Askbase in production with Docker and Kubernetes.
---

## Docker

The included `docker-compose.yml` runs the API with persistent index storage:

```bash
docker-compose up -d
```

This mounts `artifacts/`, `docs/`, and `data/` into the container. The `--seed` flag auto-ingests sample documents on first boot.

### Custom Dockerfile build

```bash
docker build -t askbase .
docker run -p 8080:8080 -v $(pwd)/artifacts:/app/artifacts askbase
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_ADMIN_TOKEN` | `admin-demo-token` | Admin API token |
| `RAG_USER_TOKEN` | `user-demo-token` | User API token |

Always override these in production.

## Kubernetes

Manifests live in the `k8s/` directory:

```
k8s/
  namespace.yaml        # Dedicated namespace
  backend-deployment.yaml   # API deployment + service
  frontend-deployment.yaml  # Frontend deployment + service
  ingress.yaml          # Ingress with TLS
```

### Deploy

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

### Health probes

The deployment uses Kubernetes-native probes:

| Probe | Endpoint | Purpose |
|-------|----------|---------|
| Liveness | `GET /health` | Restart if the process is stuck |
| Readiness | `GET /readyz` | Only route traffic when the index is loaded |

### Scaling

Askbase is stateless at the API layer. The index file is read-only after ingestion, so you can scale replicas horizontally. Mount the index from a shared volume (PVC or S3-backed) for multi-replica setups.

```yaml
# In backend-deployment.yaml
spec:
  replicas: 3
  template:
    spec:
      volumes:
        - name: index
          persistentVolumeClaim:
            claimName: askbase-index
```

### Monitoring

The `/metrics` endpoint exposes Prometheus-compatible metrics. Add a ServiceMonitor or scrape config:

```yaml
- job_name: askbase
  static_configs:
    - targets: ['askbase-api:8080']
  metrics_path: /metrics
```

Key metrics: request latency (p50/p95/p99), error rate, requests per second, index chunk count.

## Production checklist

- [ ] Override default auth tokens via environment variables
- [ ] Mount index on persistent storage
- [ ] Configure ingress with TLS
- [ ] Set up Prometheus scraping for `/metrics`
- [ ] Run `rag evaluate` against your golden dataset after each re-index
- [ ] Set resource limits (256MB RAM is enough for most indexes under 100k chunks)
