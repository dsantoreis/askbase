import { readFileSync } from "node:fs";
import { basename } from "node:path";
import type { SourceDocument } from "./types.js";

export function ingestTextFile(path: string): SourceDocument {
  const text = readFileSync(path, "utf8").trim();
  return {
    id: basename(path),
    text,
    metadata: { source: path },
  };
}
