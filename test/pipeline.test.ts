import { mkdtempSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { describe, expect, it } from "vitest";
import { RagPipeline } from "../src/pipeline.js";

describe("RagPipeline", () => {
  it("ingests docs and answers with context", async () => {
    const dir = mkdtempSync(join(tmpdir(), "rag-demo-"));
    const file = join(dir, "kb.txt");
    writeFileSync(file, "RAG usa recuperação de contexto antes de gerar resposta.");

    const pipeline = new RagPipeline();
    pipeline.ingest([file]);

    const { answer, context } = await pipeline.ask("O que RAG usa?");
    expect(context.length).toBeGreaterThan(0);
    expect(answer).toContain("Resposta (mock)");
  });
});
