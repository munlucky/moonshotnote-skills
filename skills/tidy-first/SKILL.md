---
name: tidy-first
description: Tidy First study and engineering-decision assistant backed by a public-safe ontology and knowledge graph extracted from private OCR-derived notes. Use when Codex needs to discuss small code tidying moves, when to separate tidying from behavior changes, coupling, cohesion, reversibility, options, batch size, or Kent Beck-style tidy-first sequencing without loading the full source text.
---

# Tidy First

## Use This Skill

Use this skill when the user asks about:

- tiny code cleanups before or beside behavior changes
- guard clauses, dead code removal, symmetry, helper extraction, explanatory variables, or comments
- separating structural changes from behavioral changes in commits or pull requests
- deciding whether to tidy now, later, never, or as a separate task
- coupling, cohesion, reversibility, options, and economic tradeoffs in software design

## Knowledge Boundary

This skill ships only public-safe summaries, graph nodes, graph edges, and provenance references. It does not include the full OCR text or long copied passages from the source book. Treat `references/` as a study graph, not as a replacement for the book.

The private source used to build the graph was OCR-derived text with known unclear markers. Prefer high-level explanation and engineering application. Do not quote the private source verbatim unless the user provides the relevant passage in the current conversation.

## Answer Workflow

1. Query the graph first for the user's topic:

   ```powershell
   py -3 scripts\query_graph.py --q "behavior change와 tidying 분리" --json
   ```

2. When the answer needs structured context, create a compact source pack:

   ```powershell
   py -3 scripts\expand_context.py --q "coupling cohesion reversible change" --out output\source-pack.md
   ```

3. Answer in Korean by default. Keep code identifiers and English concept names as written when they are the clearer term.

4. Use the graph as a decision aid:

   - identify the relevant tidy move or theory concept
   - explain why it applies
   - state the tradeoff
   - recommend a small next action

## Safety Rules

- Do not expose private OCR paths, raw OCR chunks, or long source excerpts.
- Do not claim the OCR source is fully reviewed; the graph is public-safe but the private OCR text still has quality caveats.
- If the user needs exact wording, ask for the passage or suggest checking the original book.

## Resources

- `references/ontology.yaml`: public ontology for node and edge types.
- `references/nodes.jsonl`, `edges.jsonl`, `chunks.jsonl`: public-safe graph.
- `references/graph_manifest.json`: provenance hash, counts, and source-quality metadata.
- `scripts/query_graph.py`: keyword query over graph nodes, edges, and chunks.
- `scripts/expand_context.py`: creates compact answer packs from graph hits.
- `scripts/validate_graph.py`: validates graph schema, source refs, counts, and public-safe flags.
