# rag-pipeline-demo

Pipeline RAG mínimo em Python com:
- ingestão de `.txt`/`.md`
- chunking com overlap
- embeddings locais simples (TF-IDF)
- retrieval por similaridade cosseno
- resposta baseada no contexto recuperado

## Requisitos
- Python 3.10+

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Uso
### 1) Ingerir documentos
```bash
python -m rag_pipeline.cli ingest data --index rag_index.pkl
```

### 2) Perguntar
```bash
python -m rag_pipeline.cli ask "o que é retrieval?" --index rag_index.pkl --top-k 3
```

## Estrutura
- `src/rag_pipeline/chunking.py` — divisão em chunks
- `src/rag_pipeline/pipeline.py` — ingestão, embeddings, retrieval, resposta, persistência
- `src/rag_pipeline/cli.py` — CLI
- `tests/test_pipeline.py` — teste básico

## Observações
- Embeddings locais via `scikit-learn` (TF-IDF), sem API externa.
- Resposta é extrativa/sumarizada do melhor chunk (demo funcional).
