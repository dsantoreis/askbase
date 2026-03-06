---
title: Architecture
---
```mermaid
flowchart LR
 UI[Next.js]-->API[FastAPI]
 API-->VDB[(Vector DB)]
 API-->INGEST[Ingestion Workers]
```
