# rag-pipeline-demo

Demo funcional de **pipeline RAG (Retrieval-Augmented Generation)** em TypeScript.

> Repositório local inicializado como privado (`"private": true` no `package.json`).

## O que o demo faz

Pipeline completo, local e sem API externa:

1. **Ingestão** de documentos texto (`docs/knowledge-base.txt`)
2. **Chunking** com overlap
3. **Indexação** em memória
4. **Retrieval** por similaridade lexical simples
5. **Resposta** com LLM mock usando contexto recuperado

## Requisitos

- Node.js 20+
- npm 10+

## Instalação

```bash
npm install
```

## Executar demo

```bash
npm run demo
# ou
./scripts/run-demo.sh
# ou com pergunta customizada
npm run demo -- "Como o chunking melhora recall?"
```

## Rodar testes

```bash
npm test
```

## Build TypeScript

```bash
npm run build
```

## Estrutura

```text
src/
  ingest.ts      # leitura de documentos
  chunk.ts       # chunking e overlap
  retriever.ts   # scoring e top-k
  llm.ts         # resposta mock
  pipeline.ts    # orquestra pipeline RAG
  demo.ts        # ponto de entrada executável
docs/
  knowledge-base.txt
test/
  chunk.test.ts
  retriever.test.ts
  pipeline.test.ts
scripts/
  run-demo.sh
```

## Próximos passos sugeridos

- Trocar retrieval lexical por embeddings reais
- Persistir índice vetorial (SQLite/pgvector)
- Adicionar avaliação automática (precision@k / recall@k)
