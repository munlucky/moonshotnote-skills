# Knowledge Pack Schema

## `graph_manifest.json`

Required fields:

- `version`
- `created_at`
- `name`
- `source_quality_gate`
- `source_paths`
- `counts`
- `public_sanitized`
- `private_source_location`

`public_sanitized` must be `true` for publishable skills.

## `nodes.jsonl`

Each line is one JSON object:

```json
{"id":"concept-example","type":"Concept","name":"Example","summary":"Short public-safe summary.","aliases":["Example"],"source_refs":[{"source":"source.txt","lines":[1,12]}],"public_safe":true}
```

Required fields: `id`, `type`, `name`, `summary`, `aliases`, `source_refs`, `public_safe`.

## `edges.jsonl`

Each line is one JSON object:

```json
{"source":"concept-a","target":"concept-b","type":"depends_on","summary":"Short relation summary.","source_refs":[{"source":"source.txt","lines":[13,20]}],"public_safe":true}
```

Required fields: `source`, `target`, `type`, `summary`, `source_refs`, `public_safe`.

## `chunks.jsonl`

Each line is one JSON object:

```json
{"id":"chunk-topic","title":"Topic","summary":"Short public-safe topic summary.","source_refs":[{"source":"source.txt","lines":[21,60]}],"keywords":["topic"],"public_safe":true}
```

Required fields: `id`, `title`, `summary`, `source_refs`, `keywords`, `public_safe`.

## Source Refs

Use line, page, section, chapter, timestamp, or stable source IDs. Do not include absolute local paths in tracked files.
