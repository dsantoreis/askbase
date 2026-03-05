export interface SourceDocument {
  id: string;
  text: string;
  metadata?: Record<string, string>;
}

export interface Chunk {
  id: string;
  documentId: string;
  text: string;
  start: number;
  end: number;
}

export interface RetrievedChunk {
  chunk: Chunk;
  score: number;
}

export interface LLMAdapter {
  generateAnswer(input: {
    question: string;
    context: Chunk[];
  }): Promise<string>;
}
