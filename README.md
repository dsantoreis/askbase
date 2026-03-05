# RAG Pipeline Demo — Enterprise Grade (Upwork-ready)

RAG pronto para propostas comerciais de **suporte interno, compliance e knowledge base corporativa**.

## O que este projeto entrega

- Ingestão robusta de `.txt` e `.md` com validações:
  - extensão permitida
  - tamanho máximo por arquivo
  - mínimo de caracteres
  - deduplicação por hash SHA-256
- Chunking configurável:
  - estratégia `char` ou `paragraph`
  - `chunk_size` + `overlap`
- Retrieval híbrido simples:
  - score lexical (TF-IDF + cosine)
  - score por interseção de termos de negócio
  - combinação ponderada
- Rerank básico:
  - bônus por cobertura de termos da query
  - bônus adicional por presença de múltiplos termos
- Persistência/caching de índice:
  - serialização do índice com versão
  - configs de ingest/retrieval embutidas no artefato
- Avaliação offline mínima:
  - `precision@k` com dataset JSONL
- API e CLI de produção:
  - CLI: `ingest`, `ask`, `evaluate`, `serve`
  - `ask` retorna resposta + citations (doc_id, offsets, score)
  - API FastAPI: `/health`, `/ask` (resposta com citations)
- Observabilidade:
  - logs estruturados em JSON
  - mensagens de erro explícitas (arquivo inválido, índice incompatível, etc.)
- Testes:
  - unitários
  - integração (API)
  - falhas/validações (ex.: arquivo grande demais)

---

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Execução rápida (happy path)

```bash
# 1) Ingestão de exemplo
python -m rag_pipeline.cli ingest data --index artifacts/rag_index.pkl

# 2) Query simples
python -m rag_pipeline.cli ask "Qual política de retenção de evidências?" --index artifacts/rag_index.pkl --top-k 3

# 3) Gate de qualidade completo (quality + API/CLI)
npm run quality:full
```

## Uso CLI

### 1) Ingestão

```bash
python -m rag_pipeline.cli ingest data \
  --index artifacts/rag_index.pkl \
  --chunk-size 500 \
  --overlap 100 \
  --chunk-strategy char \
  --max-file-mb 5 \
  --min-chars 30
```

### 2) Perguntas

```bash
python -m rag_pipeline.cli ask "Qual política de retenção de evidências?" \
  --index artifacts/rag_index.pkl \
  --top-k 3

# saída também lista citations com doc_id, intervalo e score
```

### 3) Avaliação offline (`precision@k`)

Formato `eval.jsonl` (1 linha JSON por query):

```json
{"query":"Onde guardar evidências de auditoria?","relevant_doc_ids":["/path/policy.md"]}
```

Executar:

```bash
python -m rag_pipeline.cli evaluate \
  --index artifacts/rag_index.pkl \
  --dataset eval.jsonl \
  --k 3
```

### 4) API HTTP

```bash
python -m rag_pipeline.cli serve --index artifacts/rag_index.pkl --host 0.0.0.0 --port 8080
```

Endpoints:
- `GET /health`
- `GET /metrics`
- `POST /ask`

Exemplo:

```bash
curl -X POST http://127.0.0.1:8080/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"Como tratar falha recorrente de MFA?","top_k":3}'
```

### Runbook rápido (health + metrics)

```bash
# 1) Health check
curl -s http://127.0.0.1:8080/health | jq .

# 2) Métricas estilo Prometheus
curl -s http://127.0.0.1:8080/metrics

# 3) Sanidade fim-a-fim (health + ask + metrics)
curl -s http://127.0.0.1:8080/health | jq .status
curl -s -X POST http://127.0.0.1:8080/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"How solve VPN issues?","top_k":2}' | jq .answer
curl -s http://127.0.0.1:8080/metrics | grep -E 'rag_api_(health|ask)_requests_total'
```

---

## Casos reais (alvo Upwork)

1. **Suporte Interno (IT Helpdesk):**
   - KB de runbooks e troubleshooting
   - Redução de MTTR via respostas consistentes

2. **Compliance / Auditoria:**
   - políticas internas, controles e evidências
   - consultas rápidas para times jurídicos/compliance

3. **Operations Enablement:**
   - centralização de SOPs e FAQs operacionais
   - onboarding acelerado para novos analistas

---

## ROI comercial (pitch)

- **Menos retrabalho de suporte** (respostas padronizadas + contexto certo)
- **Onboarding mais rápido** (acesso imediato a conhecimento curado)
- **Melhor governança** (base rastreável, com avaliação mínima objetiva)
- **Acelera PoC para produção** com API + CLI + persistência + testes

---

## Qualidade e testes

### Gate padrão
Roda **format check + lint + unit + smoke** em sequência.

```bash
npm run quality
```

### Gate completo (pré-publicação)
Roda gate padrão + testes de API/CLI.

```bash
npm run quality:full
```

### API/CLI
```bash
npm run test:api-cli
```

### Unit (pipeline completo)
```bash
npm run test:unit
```

### Smoke (persistência rápida)
Valida somente o ciclo `save/load` do índice, sem rodar todos os cenários do pipeline.
```bash
npm run test:persistence-smoke
```

### Checklist pré-publicação
- [ ] `npm run quality:full` passou localmente
- [ ] `python -m rag_pipeline.cli ingest ...` validado com base real
- [ ] `python -m rag_pipeline.cli ask ... --json` retornou citations
- [ ] `python -m rag_pipeline.cli serve ...` + `GET /health` + `POST /ask` testados
- [ ] README atualizado com comandos finais de validação

---

## Estrutura

- `src/rag_pipeline/chunking.py` — chunking configurável
- `src/rag_pipeline/pipeline.py` — ingestão, retrieval híbrido, rerank, persistência, avaliação
- `src/rag_pipeline/cli.py` — CLI de produção
- `src/rag_pipeline/api.py` — API FastAPI
- `src/rag_pipeline/logging_utils.py` — logs estruturados
- `tests/` — unit/integration/failure tests

---

## Limites conhecidos

- Embeddings ainda lexicais (TF-IDF); sem embedding semântico neural
- Rerank é heurístico e leve (bom para baseline comercial, não SOTA)
- Suporte de formatos está focado em `.txt`/`.md` (pode ser expandido para PDF/DOCX)

---

## Próximos upgrades sugeridos

- Adicionar embedding semântico (`sentence-transformers`) com fallback híbrido
- Re-ranking com cross-encoder para consultas críticas
- Observabilidade com OpenTelemetry + métricas de latência
- Multi-tenant index store (S3/Postgres/VectorDB)
