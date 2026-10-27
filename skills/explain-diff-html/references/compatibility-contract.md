# Compatibility Contract Reference

Machine-readable compatibility anchors. Load only for compatibility audit.

## Default Paths

- `scripts/render.py`
- `skills/explain-diff-html/SKILL.md`
- `tests/fixtures/skill-routing/public-entrypoint-cases.json`

## Hard Stops

- inspect the relevant diff and surrounding source before writing claims
- use the shared renderer instead of duplicating HTML page boilerplate
- keep secrets and unrelated private data out of generated explanations
- return the spec and rendered HTML paths with blocked evidence when rendering cannot run
