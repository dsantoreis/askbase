# Why Your Support Team Doesn't Need Another AI Chatbot

Every support tool vendor is slapping "AI-powered" on their product page. Most of them are wrappers around ChatGPT with a system prompt and a prayer.

The result: your customers get confident-sounding answers that are completely wrong, your support lead spends more time fact-checking the bot than they saved, and you're paying per-token for hallucinations.

I built Askbase because there's a simpler problem to solve first: let your team find the right answer in your own docs, instantly, with proof.

## The actual problem

Support teams don't lack intelligence. They lack retrieval.

A mid-size company has 50-200 internal docs scattered across Confluence, Google Drive, Notion, and that one engineer's personal wiki. New agents take 2 weeks to learn where things are. Senior agents forget edge cases from docs they read 8 months ago.

The fix isn't a chatbot that makes things up. It's a search engine that actually works and shows its sources.

## How Askbase works

```bash
git clone https://github.com/dsantoreis/askbase
cd askbase
docker compose up --build
```

Ingest your docs. Ask questions. Get answers grounded in your actual content, with citations pointing to the exact document and section.

```python
# Ingest docs
POST /ingest
{"source": "docs/", "format": "markdown"}

# Ask questions
POST /ask
{"query": "What's our refund policy for enterprise clients?", "top_k": 3}
```

The response includes the answer, which documents it came from, and the exact character offsets. Your team can verify any answer in seconds.

## RAG done right vs. RAG done fast

Most RAG implementations chunk documents into fixed-size blocks, embed them, and call it a day. This works for demos. In production you hit problems fast:

- **Chunk boundaries split sentences.** The answer is half in chunk 47 and half in chunk 48. Your retriever returns one of them.
- **No reranking.** Cosine similarity returns the most similar chunk, not the most relevant one. These are different things.
- **No citation tracking.** The model generates an answer but you can't trace it back to source. Your compliance team is unhappy.

Askbase uses semantic chunking that respects document structure, BM25 + vector hybrid retrieval, and character-level citation tracking. Every answer maps back to a specific location in a specific document.

## Why not just use ChatGPT?

You could upload your docs to ChatGPT and ask questions. Two problems:

1. **Your data leaves your perimeter.** For banks, insurance companies, healthcare, and anyone in the EU with GDPR obligations, this is a non-starter.
2. **No auditability.** When ChatGPT says "the refund policy is 30 days," you can't click through to see which document it read. You're trusting the model's summary of your own data.

Askbase runs on your infrastructure. Your docs stay in your network. Every answer has a paper trail.

## The Zurich angle

Switzerland's financial sector has strict data residency requirements. Your compliance officer won't approve sending client-facing knowledge bases to OpenAI's servers. Running RAG on-prem or in your own cloud tenant is the only path.

Full docs at [dsantoreis.github.io/askbase](https://dsantoreis.github.io/askbase/).

---

*Daniel Reis, Zurich. Building production AI infrastructure. [github.com/dsantoreis](https://github.com/dsantoreis)*
