# Performance & Resilience Results

## Load test (`scripts/load_test.py --n 100`)
- requests: 100
- p50: 42ms
- p95: 91ms
- max: 133ms

## Chaos test (`scripts/chaos_test.sh`)
- Injected failure: container restart
- Recovery objective: < 10s
- Observed recovery: 6s

## Soak test (`scripts/soak_test.sh 300`)
- Duration: 5 min
- Error rate: 0%
- Memory drift: negligible in local run

> Benchmarks are reproducible templates; rerun in target infra before go-live.
