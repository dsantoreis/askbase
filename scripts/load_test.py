from __future__ import annotations

import argparse
import statistics
import time

import httpx


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8080/ask")
    p.add_argument("--n", type=int, default=100)
    args = p.parse_args()

    latencies = []
    headers = {"Authorization": "Bearer user-demo-token"}
    with httpx.Client(timeout=10) as client:
        for _ in range(args.n):
            t0 = time.perf_counter()
            r = client.post(args.url, json={"query": "mfa policy", "top_k": 1}, headers=headers)
            r.raise_for_status()
            latencies.append(time.perf_counter() - t0)

    print({
        "requests": args.n,
        "p50_ms": round(statistics.median(latencies) * 1000, 2),
        "p95_ms": round(sorted(latencies)[int(args.n * 0.95) - 1] * 1000, 2),
        "max_ms": round(max(latencies) * 1000, 2),
    })


if __name__ == "__main__":
    main()
