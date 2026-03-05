# Bare Metal Deployment Guide

1. Install k3s or kubeadm cluster.
2. Install ingress-nginx.
3. Build local/published images and set imagePullSecrets if private.
4. Create namespace + secrets and apply `k8s/*.yaml`.
5. Expose ingress via DNS or reverse proxy.

Alternative: run with `docker compose up --build` for single-node demo.
