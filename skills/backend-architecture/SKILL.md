---
name: backend-architecture
description: Framework-adapter backend architecture assistant backed by a public-safe ontology distilled from FastAPI clean architecture, Tidy First, and Spring modern API graphs. Use when Codex needs to reason about backend layers, dependency direction, repository/service/use-case boundaries, DTO/schema boundaries, framework leak risks, structure versus behavior changes, coupling, cohesion, reversible architecture changes, or FastAPI/Spring adapter mapping.
---

# Backend Architecture

## Use This Skill

Use this skill when the user asks about:

- backend layer boundaries: domain, application, interface, infrastructure
- dependency direction, dependency inversion, repository abstractions, service/use-case boundaries
- DTO/schema, transaction, persistence, or framework adapter placement
- whether a framework API is leaking into application or domain code
- how to sequence backend refactors as structure changes versus behavior changes
- coupling, cohesion, change cost, and reversible architecture changes
- Spring MVC, Spring Service/Repository/JPA, OpenAPI, WebFlux, and Spring Security boundary placement

## Source Boundary

This skill is derived only from public-safe graph summaries in `fastapi-clean-architecture`, `tidy-first`, and `spring-modern-api`. It does not include private OCR source text. Treat `source_refs` as links to public graph concepts, not permission to quote original books.

It includes verified FastAPI and Spring adapters. Other framework adapters are represented only as extension points; do not invent framework-specific mappings unless the user's codebase supplies evidence.

## Answer Workflow

1. Query the graph first:

   ```powershell
   py -3 scripts\query_graph.py --q "service layer repository dependency inversion" --json
   ```

2. Load `references/framework_adapters.yaml` when the question mentions FastAPI, Spring, or framework-specific placement.

3. Create a compact source pack when the answer needs traceable context:

   ```powershell
   py -3 scripts\expand_context.py --q "FastAPI Depends layer leak" --out output\source-pack.md
   ```

4. Answer in Korean by default. Use the graph to state:

   - the relevant boundary or principle
   - the dependency direction
   - the framework adapter placement
   - the change-cost tradeoff
   - the smallest safe next action

## Decision Rules

- Inner policy code should not depend on framework or infrastructure APIs.
- Concrete infrastructure implements abstractions owned by inner policy layers.
- Controllers and routers adapt transport input into application use cases.
- DTO/schema objects belong at boundaries unless the project intentionally promotes them into domain language.
- Spring `@RestController` and FastAPI `APIRouter` are interface adapters; Spring `@Service` or application services coordinate use cases.
- Spring Data/JPA, SQLAlchemy, database sessions, and migrations are infrastructure details behind repository or persistence boundaries.
- WebFlux `Mono`/`Flux` and Spring Security filter/security-context details should not become domain model dependencies without an explicit project-level reason.
- Structural refactors and behavior changes should be split when review or rollback cost would otherwise rise.
- Decoupling is justified when expected future change-cost reduction exceeds the current structural cost.

## Resources

- `references/ontology.yaml`: node and edge type definitions.
- `references/framework_adapters.yaml`: FastAPI mapping and future adapter extension policy.
- `references/nodes.jsonl`, `edges.jsonl`, `chunks.jsonl`: public-safe architecture graph.
- `references/graph_manifest.json`: source skills, source commit, counts, and safety metadata.
- `scripts/query_graph.py`: keyword lookup over nodes, edges, chunks, and adapter mappings.
- `scripts/expand_context.py`: compact public-safe context pack writer.
- `scripts/validate_graph.py`: graph and adapter validation.
