import { describe, expect, it } from "vitest";
import { SimpleRetriever } from "../src/retriever.js";

describe("SimpleRetriever", () => {
  it("returns most relevant chunk first", () => {
    const retriever = new SimpleRetriever([
      { id: "c1", documentId: "d", text: "banana maçã fruta", start: 0, end: 18 },
      { id: "c2", documentId: "d", text: "typescript pipeline rag", start: 19, end: 44 },
    ]);

    const result = retriever.retrieve("como funciona rag pipeline", 1);
    expect(result[0]?.chunk.id).toBe("c2");
    expect(result[0]?.score).toBeGreaterThan(0);
  });
});
