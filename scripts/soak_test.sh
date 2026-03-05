#!/usr/bin/env bash
set -euo pipefail

duration=${1:-300}
end=$((SECONDS+duration))

while [ $SECONDS -lt $end ]; do
  curl -fsS -X POST http://127.0.0.1:8080/ask \
    -H 'Authorization: Bearer user-demo-token' \
    -H 'Content-Type: application/json' \
    -d '{"query":"retention policy","top_k":1}' >/dev/null
  sleep 1
done

echo "soak complete: ${duration}s"
