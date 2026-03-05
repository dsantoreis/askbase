#!/usr/bin/env bash
set -euo pipefail

echo "[chaos] restarting backend container"
docker compose restart rag-api
sleep 5
curl -fsS http://127.0.0.1:8080/health

echo "[chaos] health recovered"
