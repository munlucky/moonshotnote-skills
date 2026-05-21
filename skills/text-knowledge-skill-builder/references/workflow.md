# Text to Knowledge to Skill Workflow

## 1. Source Boundary

Classify the input before building the skill:

- `public-owned`: source can be redistributed.
- `private-owned`: source can be used locally but should not be published.
- `third-party`: publish only short summaries, metadata, and non-expressive concepts.
- `mixed`: treat as `third-party` until reviewed.

Default to `third-party` unless ownership is explicit.

## 2. Target Skill Shape

Define these before extracting knowledge:

- Skill name and trigger description.
- First 5-10 realistic user questions.
- Public/private boundary.
- Required references and scripts.
- Validation checks needed to close the work.

## 3. Private Source Pack

Use `scripts/chunk_source_text.py` to create private chunks with line provenance:

```powershell
py -3 scripts\chunk_source_text.py --source <source.txt> --out-dir skills\target-skill\output\private-source
```

Do not track the generated `output/` directory.

## 4. Public Knowledge Pack

Create these tracked files in the target skill:

- `references/ontology.yaml`
- `references/graph_manifest.json`
- `references/nodes.jsonl`
- `references/edges.jsonl`
- `references/chunks.jsonl`

Use concise summaries and source refs. Do not copy long source passages.

## 5. Skill Wrapper

The generated skill should tell future agents:

- Which reference files to load first.
- Which scripts to run for query, expansion, or validation.
- What not to expose.
- How to answer when graph coverage is weak.

## 6. Closeout

Run:

```powershell
py -3 scripts\lint_knowledge_pack.py skills\target-skill\references
py -3 scripts\audit_public_safety.py skills\target-skill
py -3 <skill-creator>\scripts\quick_validate.py skills\target-skill
npx -y skills add . --list
git status --short --ignored=matching
```
