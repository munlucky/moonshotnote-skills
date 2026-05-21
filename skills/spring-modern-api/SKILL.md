---
name: spring-modern-api
description: Spring 6 and Spring Boot 3 modern API development study assistant backed by a public-safe ontology and knowledge graph extracted from private OCR-derived notes. Use when Codex needs to explain or connect REST API design, OpenAPI design-first workflows, Spring IoC and dependency injection, Spring MVC controllers, JPA repositories, HATEOAS, ETag caching, WebFlux reactive APIs, Spring Security, JWT, OAuth2 resource servers, API testing, Docker/Kubernetes deployment, gRPC, ELK/Zipkin observability, or GraphQL API implementation without loading the full OCR source text.
---

# Spring Modern API

## Use This Skill

Use this skill when the user asks about:

- REST API design with resources, URI design, HTTP methods, status codes, HATEOAS, ETag, caching, versioning, or security
- Spring 6 and Spring Boot 3 API architecture: IoC, DI, beans, controllers, services, repositories, JPA, exception handling
- OpenAPI/OAS design-first API workflows and code generation
- reactive API design with Spring WebFlux, Reactive Streams, Mono/Flux, non-blocking pipelines, and R2DBC-style persistence boundaries
- Spring Security with JWT, refresh tokens, OAuth2 resource server, roles, CORS, and CSRF
- API testing, deployment with Docker/Kubernetes, gRPC, observability with ELK/Zipkin/Micrometer, or GraphQL schema/query/mutation/subscription patterns

## Knowledge Boundary

This skill ships only public-safe summaries, graph nodes, graph edges, topic chunks, and provenance references. It does not include the full OCR text or long copied passages from the book. The private source was OCR-derived from screenshots and contains unclear markers, so use the graph for study guidance and implementation orientation, not exact quotation.

## Answer Workflow

1. Query the graph first:

   ```powershell
   py -3 scripts\query_graph.py --q "Spring Security JWT refresh token" --json
   ```

2. Create a compact source pack when the answer needs traceable context:

   ```powershell
   py -3 scripts\expand_context.py --q "OpenAPI design-first controller exception handler" --out output\source-pack.md
   ```

3. Answer in Korean by default. Preserve code identifiers such as `@RestController`, `Mono`, `Flux`, `JWT`, `OAuth2`, `GraphQL`, and `gRPC`.

4. For implementation guidance, connect:

   - the API style or layer
   - the Spring component or tool
   - the boundary or risk
   - the smallest practical next step

## Safety Rules

- Do not expose private OCR paths, raw OCR chunks, or long source excerpts.
- Do not claim the OCR source is fully reviewed; manifest quality metadata records the OCR caveat.
- If exact wording matters, ask the user for the passage or recommend checking the original book.

## Resources

- `references/ontology.yaml`: graph schema and relation labels.
- `references/nodes.jsonl`, `edges.jsonl`, `chunks.jsonl`: public-safe study graph.
- `references/graph_manifest.json`: OCR hash, counts, and quality metadata.
- `scripts/query_graph.py`: keyword lookup over graph nodes, edges, and chunks.
- `scripts/expand_context.py`: public-safe source-pack writer.
- `scripts/validate_graph.py`: graph schema, provenance, and safety validator.
