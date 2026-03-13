# When Vector Search Beats Keyword Search (And When It Doesn't)

Everyone building RAG systems faces the same question early: vector search or keyword search? The real answer is both, but knowing when each one matters saves you from over-engineering.

I've spent the last few months building Askbase, a RAG retrieval engine for support teams. Here's what I learned about search strategies from real document collections, not toy examples.

## Keyword search isn't dead

Full-text search (BM25, TF-IDF) still wins in specific scenarios:

- **Exact product names and SKUs.** A customer searching for "ERR-4012" needs exact match, not semantic similarity to "authentication failure."
- **Compliance and legal docs.** When someone asks about "FINMA regulation 2023/01," fuzzy matching is a liability.
- **Short, specific queries.** "reset password" is already precise enough. Vector search adds latency without adding recall.

If your document corpus is under 500 pages and queries are specific, BM25 with good tokenization will outperform most vector setups.

## Where vector search changes the game

Semantic search shines when the query and the answer use different words:

- A customer asks "my screen went black" and the docs say "display output failure during sleep recovery."
- Someone searches "how to cancel" and the relevant section is titled "Subscription management."
- A support agent types "customer can't log in from new device" and the answer lives under "Multi-factor authentication device enrollment."

This mismatch between query language and document language is where keyword search fails silently. It returns nothing, or worse, returns the wrong doc because it matched on a common word.

## Hybrid search: the practical approach

In Askbase, I implemented hybrid retrieval with reciprocal rank fusion (RRF). Both search methods run in parallel, their results get merged, and the top-k chunks go to the LLM for answer generation.

The pipeline looks like this:

```
Query -> [BM25 search] -> top 20 results ─┐
                                           ├── RRF merge -> top 5 -> LLM -> answer + citations
Query -> [Vector search] -> top 20 results ┘
```

RRF is dead simple. For each document, you compute `1 / (k + rank)` for each retriever, sum the scores, and re-rank. The `k` constant (usually 60) prevents any single retriever from dominating.

Why RRF over learned re-rankers? Three reasons:
1. No training data needed. You can ship day one.
2. Adding a third retriever (metadata filter, graph lookup) is just another column in the fusion.
3. Latency stays predictable. No cross-encoder inference at query time.

## The chunking trap

Search quality depends more on how you chunk documents than which embedding model you use. I tested this with a 200-page internal knowledge base:

- **Fixed 512-token chunks:** 62% recall@5
- **Paragraph-based chunks with overlap:** 71% recall@5
- **Section-aware chunks (respect headings):** 79% recall@5
- **Section-aware + parent document retrieval:** 84% recall@5

The gap between naive chunking and section-aware chunking was bigger than the gap between any two embedding models I tested.

In Askbase, the ingestion pipeline detects document structure (Markdown headings, PDF sections, HTML tags) and chunks accordingly. Each chunk keeps a reference to its parent section so the LLM can pull in surrounding context when needed.

## What I'd skip

If you're building a RAG system for an internal team:

- **Skip fine-tuning your embedding model.** Off-the-shelf models (E5, BGE, OpenAI ada-002) are good enough for 90% of use cases. Fine-tuning matters at scale, not at 10k documents.
- **Skip knowledge graphs** unless your domain has strong entity relationships (medical, legal, financial). The engineering cost isn't worth it for most support use cases.
- **Skip agentic RAG** for v1. Multi-hop reasoning adds complexity and latency. Get single-hop retrieval right first.

## Data residency matters

One thing I kept running into with Swiss clients: data residency. Most vector databases are US-hosted. If you're handling customer data under Swiss data protection law (or GDPR), you need to know where your embeddings live.

Askbase runs entirely self-hosted. Your documents, your embeddings, your infrastructure. The Docker compose setup works on any cloud or bare metal. No data leaves your network.

This isn't a feature I added for marketing. It's a requirement from every Swiss company I talked to.

## Try it

Askbase is open source. Clone it, point it at a folder of Markdown or PDF files, and run `docker compose up`. You'll have a working retrieval API in under five minutes.

The code is at [github.com/dsantoreis/askbase](https://github.com/dsantoreis/askbase).

If you're building a support tool and need help with the retrieval layer, I'm available for consulting. Reach me on [LinkedIn](https://linkedin.com/in/dsantosreis).
