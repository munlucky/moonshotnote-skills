---
name: domain-driven-design-first-steps
description: Use this public-safe Korean study skill for Domain-Driven Design first-step questions about subdomains, ubiquitous language, bounded contexts, context maps, tactical patterns, event sourcing, CQRS, event storming, microservices, event-driven architecture, and data mesh.
license: UNLICENSED
---

# Domain-Driven Design First Steps

Use this skill when the user asks for practical Korean guidance on Domain-Driven Design concepts, study drills, architecture mapping, modernization choices, or how DDD ideas connect to FastAPI, Spring, microservices, and event-driven systems.

## Source Boundary

- The OCR text is third-party source material and is kept private under `output/private-source/`.
- Do not quote or reproduce the source text beyond brief, legally safe snippets.
- Use the public knowledge pack in `references/` as the default source of truth.
- If graph coverage is weak, say so and ask to inspect the private source locally rather than inventing missing details.
- OCR quality is useful but not final: the source run succeeded for all pages, but low-confidence review remains open.

## Workflow

1. Load `references/graph_manifest.json` to understand scope and quality gates.
2. Load `references/ontology.yaml` to see allowed node and edge types.
3. Query `references/nodes.jsonl`, `references/edges.jsonl`, and `references/chunks.jsonl` with `scripts/query_graph.py`.
4. Expand a concept with `scripts/expand_context.py` before answering with cross-topic connections.
5. Answer in Korean, favoring concise architecture tradeoffs and implementation implications.

## Useful Queries

```powershell
python scripts/query_graph.py --q "바운디드 컨텍스트"
python scripts/query_graph.py --q "이벤트 소싱 CQRS"
python scripts/expand_context.py --node bounded-context
python scripts/expand_context.py --node event-sourcing
python scripts/lint_knowledge_pack.py references
python scripts/audit_public_safety.py .
```

## Answering Rules

- Explain DDD as a decision framework for aligning software boundaries with business learning, not as a pattern checklist.
- Separate strategic design from tactical design.
- For implementation advice, first identify subdomain type, model complexity, team ownership, integration direction, and data consistency needs.
- Prefer boring implementation patterns for generic/supporting domains; reserve richer domain models, event sourcing, and CQRS for high-change or high-value domains.
- When discussing microservices, treat bounded contexts as a design input, not an automatic one-to-one service rule.
