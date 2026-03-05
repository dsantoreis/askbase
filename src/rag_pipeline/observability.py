from __future__ import annotations

import logging
import time

from fastapi import Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

REQUEST_COUNT = Counter("rag_http_requests_total", "Total HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("rag_http_request_latency_seconds", "Request latency", ["method", "path"])

logger = logging.getLogger("rag_pipeline")


def configure_logging() -> None:
    if logger.handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def metrics_endpoint() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


async def instrumented_call_next(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start

    path = request.url.path
    method = request.method
    status = str(response.status_code)

    REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
    REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)

    logger.info("request", extra={"method": method, "path": path, "status": response.status_code, "latency_s": round(elapsed, 4)})

    response.headers["X-Request-Latency"] = f"{elapsed:.4f}"
    return response
