---
name: backend-architecture
description: Registry-driven backend architecture meta-skill backed by a public-safe ontology distilled from FastAPI clean architecture, Spring modern API, Python architecture patterns, DDD first steps, Tidy First, and Modern Java backend code-quality graphs. Use when Codex needs to reason about backend layers, dependency direction, repository/service/use-case boundaries, DDD subdomains, bounded contexts, aggregates, domain events, DTO/schema boundaries, data/runtime/operations boundaries, framework leak risks, structure versus behavior changes, coupling, cohesion, reversible architecture changes, FastAPI/Spring adapter mapping, or Java Optional/Stream/CompletableFuture choices that affect Spring/backend maintainability.
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
- Java `Optional`, `Stream`, `CompletableFuture`, side-effect, async, and code-style choices that affect Spring/backend maintainability
- API design, data modeling, event-driven boundaries, monolith/microservice tradeoffs, runtime operations, testing, packaging, observability, and continuous architecture
- DDD strategic and tactical design: subdomain classification, ubiquitous language, bounded contexts, context maps, aggregates, domain events, event sourcing, CQRS, event storming, and data mesh

## Source Boundary

This v2 skill is a registry-driven meta skill. Active source skills are declared in `references/source_registry.yaml`; the curated graph currently uses public-safe summaries from `fastapi-clean-architecture`, `tidy-first`, `spring-modern-api`, `python-architecture-patterns`, `domain-driven-design-first-steps`, and `modern-java-in-action`.

It does not include private OCR source text. Treat `source_refs` as links to public graph concepts, not permission to quote original books.

`modern-java-in-action` is an adjunct backend code-quality source, not an architecture replacement. Use it only for Spring/backend readability, `Optional`, `Stream`, `CompletableFuture`, side-effect, concurrency, and async-boundary reasoning.

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

4. Answer in Korean by default. Use this fixed answer shape:

   - the situation and constraint
   - the relevant boundary or principle
   - the dependency direction
   - the framework or language placement
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
- `Optional` should document absence at lookup or API boundaries; do not use it as a universal field/DTO/persistence convention without project policy.
- `Stream` pipelines should make transformations readable; do not hide business side effects or shared mutable state inside intermediate operations.
- `CompletableFuture` belongs at explicit async boundaries where executor ownership, timeout, cancellation, and error behavior are designed.
- Data modeling and data-layer choices are architecture decisions because data is harder to replace than application code.
- Event-driven queues decouple long-running work from request paths, but add state tracking, retry, priority, and failure-handling responsibilities.
- DDD starts with business value and language: classify subdomains before choosing rich domain models, event sourcing, CQRS, or microservices.
- Bounded contexts are semantic and ownership boundaries; they inform service boundaries but should not be mapped one-to-one to services automatically.
- Aggregates are transaction and invariant boundaries; repositories should usually load and save aggregates instead of exposing arbitrary persistence internals.
- Observability, testing, packaging, and profiling/debugging evidence should feed architecture evolution instead of being treated as afterthoughts.
- Structural refactors and behavior changes should be split when review or rollback cost would otherwise rise.
- Decoupling is justified when expected future change-cost reduction exceeds the current structural cost.

## Resources

- `references/ontology.yaml`: node and edge type definitions.
- `references/source_registry.yaml`: active public-safe source skill registry for v2 synthesis.
- `references/framework_adapters.yaml`: FastAPI mapping and future adapter extension policy.
- `references/nodes.jsonl`, `edges.jsonl`, `chunks.jsonl`: public-safe architecture graph.
- `references/graph_manifest.json`: source registry path, source skills, counts, and safety metadata.
- `scripts/build_from_source_skills.py`: registry and curated source-ref coverage validation.
- `scripts/query_graph.py`: keyword lookup over nodes, edges, chunks, and adapter mappings.
- `scripts/expand_context.py`: compact public-safe context pack writer.
- `scripts/validate_graph.py`: graph and adapter validation.
