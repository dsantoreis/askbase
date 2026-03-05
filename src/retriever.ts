import type { Chunk, RetrievedChunk } from "./types.js";

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .split(/\s+/)
    .filter(Boolean);
}

function vectorize(tokens: string[]): Map<string, number> {
  const map = new Map<string, number>();
  for (const token of tokens) {
    map.set(token, (map.get(token) ?? 0) + 1);
  }
  return map;
}

function cosine(a: Map<string, number>, b: Map<string, number>): number {
  let dot = 0;
  let magA = 0;
  let magB = 0;

  for (const value of a.values()) magA += value * value;
  for (const value of b.values()) magB += value * value;

  const [small, large] = a.size <= b.size ? [a, b] : [b, a];
  for (const [token, value] of small) {
    dot += value * (large.get(token) ?? 0);
  }

  if (magA === 0 || magB === 0) return 0;
  return dot / (Math.sqrt(magA) * Math.sqrt(magB));
}

export class SimpleRetriever {
  private readonly chunkVectors: { chunk: Chunk; vector: Map<string, number> }[];

  constructor(chunks: Chunk[]) {
    this.chunkVectors = chunks.map((chunk) => ({
      chunk,
      vector: vectorize(tokenize(chunk.text)),
    }));
  }

  retrieve(query: string, topK = 3): RetrievedChunk[] {
    const queryVector = vectorize(tokenize(query));

    return this.chunkVectors
      .map(({ chunk, vector }) => ({
        chunk,
        score: cosine(queryVector, vector),
      }))
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, topK);
  }
}
