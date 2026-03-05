import { chunkDocument, type ChunkOptions } from "./chunk.js";
import { ingestTextFile } from "./ingest.js";
import { MockLLMAdapter } from "./llm.js";
import { SimpleRetriever } from "./retriever.js";
import type { Chunk, LLMAdapter } from "./types.js";

export interface RagPipelineOptions {
  chunk: ChunkOptions;
  topK: number;
}

export class RagPipeline {
  private readonly llm: LLMAdapter;
  private readonly options: RagPipelineOptions;
  private chunks: Chunk[] = [];
  private retriever: SimpleRetriever | null = null;

  constructor(
    llm: LLMAdapter = new MockLLMAdapter(),
    options: RagPipelineOptions = { chunk: { chunkSize: 120, overlap: 20 }, topK: 3 },
  ) {
    this.llm = llm;
    this.options = options;
  }

  ingest(paths: string[]): void {
    this.chunks = paths.flatMap((path) => {
      const doc = ingestTextFile(path);
      return chunkDocument(doc, this.options.chunk);
    });
    this.retriever = new SimpleRetriever(this.chunks);
  }

  async ask(question: string): Promise<{ answer: string; context: Chunk[] }> {
    if (!this.retriever) {
      throw new Error("Pipeline not initialized. Run ingest() first.");
    }

    const retrieved = this.retriever.retrieve(question, this.options.topK);
    const context = retrieved.map((item) => item.chunk);
    const answer = await this.llm.generateAnswer({ question, context });

    return { answer, context };
  }
}
