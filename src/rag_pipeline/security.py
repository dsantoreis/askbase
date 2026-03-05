from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class AuthContext:
    subject: str
    role: str


class AuthManager:
    def __init__(self) -> None:
        self._tokens = {
            os.getenv("RAG_ADMIN_TOKEN", "admin-demo-token"): AuthContext(subject="admin", role="admin"),
            os.getenv("RAG_USER_TOKEN", "user-demo-token"): AuthContext(subject="user", role="user"),
        }

    def authenticate(self, request: Request) -> AuthContext:
        header = request.headers.get("authorization", "")
        if not header.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        token = header.split(" ", 1)[1].strip()
        ctx = self._tokens.get(token)
        if not ctx:
            raise HTTPException(status_code=401, detail="invalid token")
        return ctx

    @staticmethod
    def require_role(ctx: AuthContext, role: str) -> None:
        if ctx.role != role:
            raise HTTPException(status_code=403, detail=f"requires role={role}")


class InMemoryRateLimiter:
    def __init__(self, limit: int = 30, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> tuple[int, int]:
        now = time.time()
        cutoff = now - self.window_seconds
        bucket = self._buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.limit:
            retry_after = int(max(1, self.window_seconds - (now - bucket[0])))
            raise HTTPException(status_code=429, detail=f"rate limit exceeded; retry_after={retry_after}s")
        bucket.append(now)
        remaining = max(0, self.limit - len(bucket))
        return self.limit, remaining
