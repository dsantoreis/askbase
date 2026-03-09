# Troubleshooting Guide

## Common Issues

### "Index not loaded" error when querying
**Symptom**: POST /ask returns `{"detail": "index not loaded"}`.
**Cause**: The server started but no index file was found at the configured path.
**Fix**: Run `rag ingest ./docs --index artifacts/rag_index.pkl` to build the index, then restart the server. Alternatively, use `--seed` mode which auto-ingests sample documents on first run.

### Authentication fails with 401
**Symptom**: API returns `{"detail": "missing bearer token"}` or `{"detail": "invalid token"}`.
**Cause**: The Authorization header is missing or the token does not match RAG_ADMIN_TOKEN or RAG_USER_TOKEN.
**Fix**: Ensure your request includes `Authorization: Bearer <token>`. Check that your .env file has the correct token values and the server was restarted after changes.

### Rate limit exceeded (429)
**Symptom**: API returns HTTP 429 with `rate limit exceeded`.
**Cause**: More than 30 requests were made from the same client IP within 60 seconds.
**Fix**: Wait for the retry_after period specified in the response. For higher limits, adjust the InMemoryRateLimiter configuration or deploy behind a load balancer to distribute traffic.

### Empty or low-quality answers
**Symptom**: Answers return generic text or irrelevant citations.
**Cause**: The query terms do not match the vocabulary in your indexed documents, or document coverage is insufficient.
**Fix**:
1. Use specific terms that appear in your documents
2. Increase top_k to retrieve more context (up to 10)
3. Ensure relevant documents have been ingested
4. Re-ingest with smaller chunk_size (e.g., 150) for more granular retrieval

### Docker container exits immediately
**Symptom**: `docker-compose up` starts the container but it exits with code 1.
**Cause**: The artifacts directory does not exist or the index file is corrupted.
**Fix**: Ensure the `artifacts/` directory exists (`mkdir -p artifacts`). If the index is corrupted, delete it and re-ingest: `rag ingest ./docs --index artifacts/rag_index.pkl`.

### Frontend cannot reach backend
**Symptom**: Chat page shows "Failed to fetch" or network errors.
**Cause**: The NEXT_PUBLIC_API_URL environment variable points to the wrong backend address.
**Fix**: Set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8080` in the frontend environment. When running in Docker, use the service name: `http://rag-api:8080`.

### PDF documents not ingesting
**Symptom**: PDF files are skipped during ingestion or produce empty chunks.
**Cause**: The PDF may be image-based (scanned) rather than text-based, or pypdf cannot extract text.
**Fix**: Ensure PDFs contain selectable text. For scanned documents, run OCR first (e.g., using Tesseract) and save as text before ingesting.

## Performance Tuning

### Slow query response times
- Check the number of indexed chunks: more chunks = slower search
- Reduce top_k if you don't need many citations
- Consider splitting large document collections into domain-specific indexes

### High memory usage
- TF-IDF indexes are loaded entirely into memory
- For large corpora (>100k chunks), consider deploying with more RAM or splitting into multiple indexes
- Monitor with `/metrics` endpoint for request patterns

## Getting Help

- Check the FAQ: common questions are answered in the knowledge base
- API docs: all endpoints are documented in the product guide
- Open an issue on GitHub for bugs or feature requests
- Enterprise customers: contact support@askbase.io for priority assistance
