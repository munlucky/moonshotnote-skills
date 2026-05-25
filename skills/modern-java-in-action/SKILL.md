---
name: modern-java-in-action
description: Modern Java study assistant backed by a public-safe graph extracted from private OCR-derived notes. Use when Codex needs to reason about Java lambdas, functional interfaces, streams, collectors, Optional, default methods, date/time APIs, CompletableFuture, reactive/concurrent programming foundations, and Java code style choices that affect Spring/backend code readability and maintainability without loading full OCR source text.
---

# Modern Java In Action

## Use This Skill

Use this skill when the user asks about:

- Java lambda expressions, method references, behavior parameterization, or functional interfaces
- Stream API pipelines, collectors, grouping, reduction, parallel stream risks, and side-effect control
- `Optional` as a null-handling boundary and when not to use it
- default methods and interface evolution
- Java date/time API usage in backend models and DTOs
- `CompletableFuture`, asynchronous composition, and reactive/concurrency foundations
- improving Java/Spring backend examples so they use modern Java idioms without hiding architecture boundaries

## Knowledge Boundary

This skill ships only public-safe summaries, graph nodes, graph edges, topic chunks, and provenance references. It does not include the full OCR text or long copied passages from the book. The private source is OCR-derived and should be used as study guidance, not exact quotation.

## Answer Workflow

1. Query the graph first:

   ```powershell
   py -3 scripts\query_graph.py --q "streams collectors optional completablefuture" --json
   ```

2. Create a compact public-safe source pack when traceable context is useful:

   ```powershell
   py -3 scripts\expand_context.py --q "lambda stream side effects optional backend" --out output\source-pack.md
   ```

3. Answer in Korean by default. Preserve identifiers such as `Stream`, `Optional`, `Collector`, `CompletableFuture`, `Function`, `Predicate`, `Mono`, and `Flux`.

4. For backend study material, connect:

   - the Java language feature
   - the backend architecture boundary it affects
   - readability, concurrency, null-safety, or side-effect risk
   - the smallest practical refactoring or test

## Decision Rules

- Use lambdas and method references to express behavior clearly; do not hide business policy inside long anonymous pipelines.
- Keep stream operations stateless and side-effect-light unless a deliberate terminal operation or collector owns mutation.
- Use `Optional` mainly at absence boundaries; avoid using it as a field or DTO shape without a project-level convention.
- Treat parallel streams as a performance decision that needs measurement and side-effect review.
- Use `CompletableFuture` only when async composition, timeout, exception handling, and executor ownership are explicit.
- In Spring/backend examples, modern Java idioms should clarify use cases and DTO mapping, not replace architecture boundaries.

## Resources

- `references/ontology.yaml`: graph schema and relation labels.
- `references/nodes.jsonl`, `edges.jsonl`, `chunks.jsonl`: public-safe study graph.
- `references/graph_manifest.json`: OCR hash, counts, and quality metadata.
- `scripts/query_graph.py`: keyword lookup over graph nodes, edges, and chunks.
- `scripts/expand_context.py`: public-safe source-pack writer.
- `scripts/validate_graph.py`: graph schema, provenance, and safety validator.
