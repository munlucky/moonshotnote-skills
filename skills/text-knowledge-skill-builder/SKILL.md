---
name: text-knowledge-skill-builder
description: Convert long source text, notes, transcripts, exported documents, manuals, or verified text files into public-safe Codex skills backed by structured knowledge, ontology, chunks, graph nodes, graph edges, provenance, and validation gates. Use when Codex needs to transform text into reusable skill behavior while separating private source material from publishable summaries and checking copyright, privacy, local-path, and secret leakage risks.
---

# Text Knowledge Skill Builder

## Overview

Use this skill to turn source text into a reusable Codex skill through a `text -> private extraction -> public-safe knowledge graph -> skill` pipeline. The default is **maximal source-knowledge use with lossy public abstraction**: read the actual source chunks, extract as much reusable concept/decision/warning/relation knowledge as possible, and publish only rewritten, non-expressive graph artifacts that cannot substitute for the source.

## Workflow

1. Define the target skill contract: name, intended users, trigger phrases, public/private boundary, source ownership lane, and first useful queries.
2. Prepare private source with `scripts/chunk_source_text.py`, writing output under the target skill's ignored `output/private-source/` directory.
3. Read every `source_chunks.jsonl` row, including `text`, and triage each chunk as semantic, low-signal, duplicate, OCR-bad, code-heavy, table-heavy, exercise-heavy, or source-structure-only.
4. Create a private-only candidate ledger under ignored `output/extraction-candidates/<run-id>/`. Candidate rows should record source chunk id, line range, semantic signals, extraction kind, blocked/dropped material flags, abstraction loss, review status, and a hash of private evidence. Do not put source sentences in tracked files.
5. Rewrite accepted candidates into public-safe `references/ontology.yaml`, `references/graph_manifest.json`, `references/nodes.jsonl`, `references/edges.jsonl`, `references/chunks.jsonl`, plus `coverage_matrix.jsonl` and `query_qa.jsonl` when coverage or retrievability matters.
6. Attach public-safe `transform_trace` to every public row. Source skills should trace to source chunk id, line range, candidate hash, extraction kind, abstraction loss, dropped material flags, and review status. Meta skills should trace only to source skill public graph IDs.
7. Validate that public rows are chunk-grounded, not just source-referenced: non-query rows must have `source_refs`/`line_range` overlapping their `transform_trace.line_range`; edges must have shared or explicit evidence; backend/meta promotion must not read private source directly.
8. Write a concise `SKILL.md`, `agents/openai.yaml`, and query/expand/validate scripts when they materially improve reuse.
9. Audit before publishing with schema, public-safety, verbatim, forbidden-material, substitution-risk, grounding, coverage, query, and install-discovery gates.

## Knowledge Contract

- Tracked references contain summaries, normalized labels, relationships, public-safe traces, and source refs only.
- Private source files, raw chunks, full transcripts, exports, and intermediate artifacts live under ignored `output/`.
- Every public node, edge, chunk, coverage row, and query QA row must have `source_refs` where applicable, `public_safe: true`, and `transform_trace` unless the target skill is explicitly non-source-derived.
- `transform_trace` must never contain source text, OCR fragments, absolute local paths, private chunk paths, or source code. Use stable chunk ids, line ranges, candidate digests, and review/risk labels only.
- Use source knowledge deeply, but publish it as lossy abstraction. Do not copy source wording, preserve examples, reproduce tables, retain exercises, or rebuild the source's chapter-by-chapter teaching path.
- Code-heavy, table-heavy, and exercise-heavy chunks may inform concepts only after the protected material is marked as dropped and the public row passes forbidden-material and verbatim gates.
- Prefer domain-specific ontology types over generic buckets once the target skill's domain is clear.
- Do not create a full-text search substitute for copyrighted or private material unless the user explicitly owns and wants that distribution.
- If a row cannot be grounded to an overlapping source chunk or reviewed extraction record, mark it as a coverage gap or remove it. Do not attach an unrelated accepted candidate as fallback evidence.

## Resources

- Read `references/workflow.md` when planning a new text-to-skill conversion.
- Read `references/knowledge-pack-schema.md` when creating or reviewing graph files.
- Read `references/public-safety-checklist.md` before publishing or pushing generated skill files.
- Use `scripts/chunk_source_text.py` to create private source chunks with line provenance.
- Use `scripts/lint_knowledge_pack.py` to validate graph schema, counts, source refs, and orphan nodes.
- Use `scripts/audit_public_safety.py` to scan tracked publishable files for local paths, personal data, secrets, and raw-source leakage.
- When the target repository has stronger public graph gates, prefer them. For the moonshotnote-skills style, run or create equivalents of: `validate_chunk_grounding.py`, `validate_transform_trace.py`, `validate_forbidden_material.py`, `validate_substitution_risk.py`, `validate_no_manifest_only_generation.py`, `validate_coverage_matrix.py`, `validate_query_qa.py`, and `audit_public_verbatim.py`.

## Closeout Rules

Do not call the work complete until the generated skill installs, graph validation passes, public safety audit passes, chunk-grounding and transform-trace checks pass, verbatim/forbidden-material/substitution-risk checks pass, and `git status` shows no raw private source or private candidate ledger as a tracked candidate.
