import type { Chunk, LLMAdapter } from "./types.js";

export class MockLLMAdapter implements LLMAdapter {
  async generateAnswer(input: {
    question: string;
    context: Chunk[];
  }): Promise<string> {
    const excerpt = input.context.map((chunk) => chunk.text.trim()).join("\n---\n");
    return [
      `Pergunta: ${input.question}`,
      "Resposta (mock): baseado no contexto recuperado, o tema central é RAG com chunking e recuperação simples.",
      `Contexto utilizado:\n${excerpt || "(nenhum)"}`,
    ].join("\n\n");
  }
}
