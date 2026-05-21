---
name: text-knowledge-skill-builder
description: Convert long source text, notes, transcripts, exported documents, manuals, or verified text files into public-safe Codex skills backed by structured knowledge, ontology, chunks, graph nodes, graph edges, provenance, and validation gates. Use when Codex needs to transform text into reusable skill behavior while separating private source material from publishable summaries and checking copyright, privacy, local-path, and secret leakage risks.
---

# Text Knowledge Skill Builder

## Overview

Use this skill to turn source text into a reusable Codex skill through a `text -> knowledge -> skill` pipeline. Keep source text private by default; publish only the minimal summaries, ontology, graph, scripts, and provenance needed for reliable reuse.

## Workflow

1. Define the target skill contract: name, intended users, trigger phrases, public/private boundary, and first useful queries.
2. Prepare private source with `scripts/chunk_source_text.py`, writing output under the target skill's ignored `output/private-source/` directory.
3. Extract public-safe knowledge into `references/ontology.yaml`, `references/graph_manifest.json`, `references/nodes.jsonl`, `references/edges.jsonl`, and `references/chunks.jsonl`.
4. Write a concise `SKILL.md`, `agents/openai.yaml`, and query/expand/validate scripts when they materially improve reuse.
5. Audit before publishing with `scripts/lint_knowledge_pack.py` and `scripts/audit_public_safety.py`.
6. Validate installation with the skill creator validator and `npx skills add . --list`.

## Knowledge Contract

- Tracked references contain summaries, normalized labels, relationships, and source refs only.
- Private source files, raw chunks, full transcripts, exports, and intermediate artifacts live under ignored `output/`.
- Every public node, edge, and chunk must have `source_refs` and `public_safe: true`.
- Prefer domain-specific ontology types over generic buckets once the target skill's domain is clear.
- Do not create a full-text search substitute for copyrighted or private material unless the user explicitly owns and wants that distribution.

## Resources

- Read `references/workflow.md` when planning a new text-to-skill conversion.
- Read `references/knowledge-pack-schema.md` when creating or reviewing graph files.
- Read `references/public-safety-checklist.md` before publishing or pushing generated skill files.
- Use `scripts/chunk_source_text.py` to create private source chunks with line provenance.
- Use `scripts/lint_knowledge_pack.py` to validate graph schema, counts, source refs, and orphan nodes.
- Use `scripts/audit_public_safety.py` to scan tracked publishable files for local paths, personal data, secrets, and raw-source leakage.

## Closeout Rules

Do not call the work complete until the generated skill installs, graph validation passes, public safety audit passes, and `git status` shows no raw private source as a tracked candidate.
