# Architecture Notes

- Ingestion: recursive loader for `.pdf`, `.txt`, `.md`
- Chunking: deterministic sliding window (`chunk_size`, `overlap`)
- Embeddings: TF-IDF vector space model
- Retrieval: cosine similarity, top-k ranking
- Answering: extractive grounded response + citation list
- Evaluation: `context_precision@k` from JSONL fixtures
