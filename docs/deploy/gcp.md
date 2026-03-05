# GCP Deployment Guide

1. Build images and push to Artifact Registry.
2. Provision GKE Autopilot cluster.
3. Apply namespace, deployments, services, ingress.
4. Configure Secret Manager sync for `rag-secrets`.
5. Use Managed Prometheus to scrape `/metrics`.

Recommended: Cloud Armor in front of ingress.
