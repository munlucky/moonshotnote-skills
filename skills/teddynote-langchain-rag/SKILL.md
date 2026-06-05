---
name: teddynote-langchain-rag
description: Use this skill for public-safe reasoning about RAG and LangChain pipelines, document loading, splitting, embedding, vector stores, retrievers, prompts, chains, evaluation, deployment, and troubleshooting.
---

# Teddynote-langchain-rag

Use this skill with the public-safe knowledge graph in `references/`. The private OCR source is intentionally excluded from tracked files.

## Load Order

1. Read `references/ontology.yaml`.
2. Search `references/chunks.jsonl` for topic clusters.
3. Use `references/nodes.jsonl` and `references/edges.jsonl` to connect decisions, warnings, and workflows.
4. Use `references/coverage_matrix.jsonl` and `references/query_qa.jsonl` to inspect coverage and retrievability.

## Public Boundary

Do not quote or reconstruct the private OCR text. Use the graph as lossy abstraction and keep answers educational.
