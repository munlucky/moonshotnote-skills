---
name: python-architecture-patterns
description: >-
  Use when Codex needs to explain or connect Python-oriented software architecture patterns from a public-safe knowledge graph covering API design, data modeling, data layers, Twelve-Factor services, web server structure, event-driven architecture, monolith vs microservices, testing and TDD, packaging, logging, metrics, profiling, debugging, and continuous architecture. Source text is third-party OCR-derived material; use summaries and graph references only, not raw source reproduction.
---

# Python Architecture Patterns

Use this skill to answer architecture questions using a public-safe knowledge pack distilled from a reviewed OCR source.

## Source Boundary

- Treat the source as `third-party`.
- Do not quote or reconstruct long passages from the source.
- Public files contain only short summaries, concept labels, graph edges, and line provenance.
- Raw reviewed OCR chunks live under ignored `output/private-source/` and are not part of publishable skill behavior.

## How To Use

1. Read `references/graph_manifest.json` first to understand source quality and coverage.
2. Read `references/ontology.yaml` for node and edge types.
3. Use `scripts/query_knowledge.py <keyword>` for quick lookup across public nodes and chunks.
4. Load `references/nodes.jsonl`, `references/edges.jsonl`, and `references/chunks.jsonl` only as needed.
5. Answer from public summaries and relationships. If graph coverage is weak, say that the knowledge pack has limited coverage and ask whether to inspect private source locally.

## Good Questions

- API 설계와 데이터 모델링은 어떤 순서로 연결되는가?
- 모노리스와 마이크로서비스 선택 기준은 무엇인가?
- 이벤트 기반 구조를 언제 도입해야 하는가?
- 로깅, 메트릭, 프로파일링, 디버깅은 각각 어떤 증거를 제공하는가?
- 테스트/TDD와 지속적인 아키텍처 개선은 어떻게 연결되는가?
- Python 패키지 관리는 아키텍처 경계와 어떤 관계가 있는가?

## Guardrails

- Do not provide full chapter summaries that substitute for the book.
- Do not expose local paths, raw OCR chunks, or private-source files.
- Prefer tradeoff-focused architectural guidance over source recap.
- Mark uncertainty when an answer depends on unreadable OCR spans.
