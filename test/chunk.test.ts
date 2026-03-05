import { describe, expect, it } from "vitest";
import { chunkDocument } from "../src/chunk.js";

describe("chunkDocument", () => {
  it("creates overlapping chunks", () => {
    const chunks = chunkDocument(
      { id: "doc1", text: "abcdefghijklmnopqrstuvwxyz" },
      { chunkSize: 10, overlap: 2 },
    );

    expect(chunks.length).toBe(3);
    expect(chunks[1]?.start).toBe(8);
    expect(chunks[2]?.text).toBe("qrstuvwxyz");
  });
});
