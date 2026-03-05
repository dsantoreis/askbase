# AWS Deployment Guide

1. Build and push images to ECR.
2. Create EKS cluster + ingress controller.
3. Create secret `rag-secrets` with admin/user tokens.
4. Apply manifests in `k8s/`.
5. Attach CloudWatch scraping for `/metrics`.

Recommended: ALB ingress + HPA on p95 latency.
