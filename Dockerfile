FROM python:3.11-slim AS builder
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install build && python -m build

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /app/dist/*.whl /tmp/pkg.whl
RUN pip install --no-cache-dir /tmp/pkg.whl
EXPOSE 8080
CMD ["python", "-m", "rag_pipeline.cli", "serve", "--host", "0.0.0.0", "--port", "8080", "--index", "artifacts/rag_index.pkl"]
