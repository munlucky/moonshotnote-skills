---
name: fastapi-clean-architecture
description: FastAPI and clean architecture study assistant backed by a public-safe ontology and knowledge graph extracted from verified OCR notes. Use when Codex needs to explain or connect concepts such as FastAPI, APIRouter, Depends, Pydantic schemas, repository pattern, service layer, dependency inversion, SQLAlchemy, Alembic, JWT login, authentication/authorization, CRUD, or the book-specific TIL service architecture without loading the full OCR source text.
---

# FastAPI Clean Architecture

## Overview

Use this skill to answer FastAPI and clean architecture questions from the bundled ontology graph. The tracked references are public-safe summaries only; never infer that the full OCR text is bundled in the skill.

## Workflow

1. Start with `references/graph_manifest.json` to check graph version, source quality gates, and counts.
2. Use `scripts/query_graph.py --q "<question>" --json` to find matching nodes, chunks, and relations.
3. Use `scripts/expand_context.py --q "<question>" --out <path>` when a compact source pack is useful before answering or drafting code guidance.
4. Load `references/ontology.yaml` only when the user asks about schema, graph construction, or relation semantics.
5. Treat `source_refs` as provenance pointers, not as permission to quote the original book. Keep answers in Korean by default and preserve code identifiers exactly.

## Boundaries

- Do not claim the bundled graph is a full book transcription.
- Do not expose private OCR source paths unless the user is working locally and explicitly needs source diagnostics.
- Do not quote long passages from OCR source text. Use short paraphrases and cite graph node IDs or source refs.
- Keep `moonshotnote-ocr` responsible for OCR extraction and visual review. This skill consumes verified OCR artifacts and graph references.

## Resources

- `references/nodes.jsonl`: public-safe graph nodes.
- `references/edges.jsonl`: public-safe relations between nodes.
- `references/chunks.jsonl`: public-safe topic chunks with source refs.
- `references/ontology.yaml`: node types, relation labels, and required fields.
- `scripts/query_graph.py`: keyword graph lookup.
- `scripts/expand_context.py`: source-pack writer.
- `scripts/validate_graph.py`: schema, provenance, and public-safety validator.
- `scripts/prepare_private_source.py`: local-only helper that records absolute OCR source metadata under ignored `output/private-source/`.

## Answering Rules

When answering implementation questions, connect the relevant graph concepts first, then provide pragmatic code guidance. If the graph has weak coverage for a question, say that the bundled v1 graph is core-structure only and continue from general FastAPI knowledge with that limitation stated.
