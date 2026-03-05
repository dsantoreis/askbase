import { RagPipeline } from "./pipeline.js";

async function main(): Promise<void> {
  const pipeline = new RagPipeline();
  pipeline.ingest(["docs/knowledge-base.txt"]);

  const question = process.argv.slice(2).join(" ") || "O que é RAG e por que usar chunking?";
  const result = await pipeline.ask(question);

  console.log("=== CONTEXTO RECUPERADO ===");
  for (const chunk of result.context) {
    console.log(`- ${chunk.id} [${chunk.start}-${chunk.end}]`);
  }

  console.log("\n=== RESPOSTA ===");
  console.log(result.answer);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
