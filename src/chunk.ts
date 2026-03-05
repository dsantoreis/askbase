import type { Chunk, SourceDocument } from "./types.js";

export interface ChunkOptions {
  chunkSize: number;
  overlap: number;
}

export function chunkDocument(
  doc: SourceDocument,
  options: ChunkOptions,
): Chunk[] {
  const { chunkSize, overlap } = options;
  if (chunkSize <= 0) throw new Error("chunkSize must be > 0");
  if (overlap < 0 || overlap >= chunkSize) {
    throw new Error("overlap must be >= 0 and < chunkSize");
  }

  const chunks: Chunk[] = [];
  let start = 0;
  let idx = 0;

  while (start < doc.text.length) {
    const end = Math.min(start + chunkSize, doc.text.length);
    chunks.push({
      id: `${doc.id}#${idx}`,
      documentId: doc.id,
      text: doc.text.slice(start, end),
      start,
      end,
    });
    idx += 1;
    if (end === doc.text.length) break;
    start = end - overlap;
  }

  return chunks;
}
