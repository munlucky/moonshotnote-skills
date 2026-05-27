# Codebase Graph Schema

## File Location

Default graph path:

```text
<repo-root>/.codebase-understanding/codebase-map.json
```

The output directory is local scratch by default. Commit it only when the user explicitly wants a durable repository map.

## Root Object

```json
{
  "version": "0.2.0",
  "schemaVersion": 2,
  "kind": "codebase",
  "generatedAt": "ISO-8601 timestamp",
  "project": {
    "name": "repo-name",
    "root": "absolute path",
    "gitCommitHash": "sha or unknown",
    "languages": ["python", "typescript"],
    "frameworkHints": ["fastapi", "react"],
    "analysis": {
      "schemaVersion": 2,
      "deterministicAnalyzer": "0.2.0",
      "semanticAnalyzer": "0.2.0",
      "semanticMode": "heuristic",
      "semanticCoverage": {
        "annotatedNodes": 42,
        "candidateFileNodes": 120
      }
    },
    "resolver": {
      "typescript": {
        "configs": [
          {
            "configPath": "tsconfig.json",
            "baseUrl": "absolute path",
            "pathMappings": 3,
            "extends": "./tsconfig.base.json"
          }
        ],
        "configCount": 1,
        "pathMappings": 3
      }
    }
  },
  "nodes": [],
  "edges": [],
  "layers": [],
  "tour": [],
  "summary": {}
}
```

## Nodes

Common node fields:

- `id`: stable string id.
- `type`: `file`, `function`, `class`, `module`, `config`, `document`, `service`, `endpoint`, `pipeline`, `schema`, `resource`, or `test`.
- `name`: human-readable name.
- `filePath`: repository-relative POSIX path when backed by a file.
- `lineRange`: `[start, end]` for symbols when available.
- `summary`: deterministic, compact summary.
- `responsibility`: semantic role or reason this node exists.
- `evidence`: source path and optional line ranges used to justify summaries.
- `confidence`: `0.0` to `1.0` confidence score for generated metadata.
- `layerReason`: why the node was placed in its layer.
- `riskHints`: review/change risks inferred from size, role, dependency degree, or naming.
- `languageNotes`: parser/resolver notes and language-specific caveats.
- `tags`: language, layer, and category tags.
- `complexity`: `simple`, `moderate`, or `complex`.

ID convention:

- File: `file:<path>`
- Symbol: `function:<path>:<name>` or `class:<path>:<name>`

## Edges

Allowed edge types:

- `contains`: file contains symbol.
- `imports`: file imports another internal file.
- `tested_by`: production file is tested by a test file.
- `configures`: config file affects a runtime or package surface.
- `documents`: document describes a project or component.
- `related`: weak heuristic relationship.

Edge fields:

- `source`: source node id.
- `target`: target node id.
- `type`: edge type.
- `direction`: usually `forward`.
- `weight`: `0.0` to `1.0`.
- `description`: optional short explanation.

## Layers

Layers are heuristic groups inferred from paths and filenames:

- `interface`: API routes, controllers, pages, UI components.
- `application`: services, use cases, commands, handlers.
- `domain`: models, entities, aggregates, policies.
- `data`: repositories, database, migrations, persistence.
- `infrastructure`: deployment, Docker, CI, cloud, package plumbing.
- `tests`: tests, fixtures, specs.
- `docs`: README and documentation.
- `utility`: shared helpers.
- `unknown`: no confident placement.

Use layers as a navigation aid, not as a final architecture judgment. UI-oriented TypeScript CLIs often put Ink screens, React hooks, and components in the `interface` layer while command, tool, task, query, and remote/session orchestration files fall into `application`.

## Query Strategy

1. Search the graph by file path, symbol name, summary, tags, and layer.
2. Expand matching nodes by one hop through edges.
3. Read the actual files for the matched nodes.
4. Answer with source-backed claims and identify uncertainty.

For diff impact, map changed files to file nodes, include contained symbols, then expand one hop. Treat unmapped changed files as stale-graph evidence and refresh the graph when risk matters.

## Consumer Artifacts

- `understand_codebase.py` is the default entrypoint. It provides `analyze`, `semantic`, `dashboard`, `chat`, `diff`, `explain`, `onboard`, and `study` subcommands, with `analyze` saving graph artifacts, generating semantic packs/annotations, and opening the dashboard by default.
- `semantic_graph.py` writes `.codebase-understanding/semantic-packs/*.jsonl`, creates `.codebase-understanding/semantic-annotations.json`, and merges semantic fields into `codebase-map.json`.
- `build_chat_prompt.py` turns a query context into an LLM-ready prompt.
- `explain_graph.py` turns one file, symbol, or node into a focused explanation context.
- `study` mode writes `.codebase-understanding/reports/study/*.md`, including ranked overview, preset-oriented chapters, hotspots, and file index.
- `write_diff_overlay.py` writes `diff-overlay.json`:

```json
{
  "version": "0.2.0",
  "baseBranch": "working-tree",
  "generatedAt": "ISO-8601 timestamp",
  "changedFiles": ["src/foo.ts"],
  "changedNodeIds": ["file:src/foo.ts"],
  "affectedNodeIds": ["file:src/bar.ts"],
  "unmappedFiles": [],
  "risk": {
    "level": "medium",
    "score": 2,
    "reasons": ["moderate blast radius: 8 affected nodes"]
  }
}
```

- `serve_dashboard.py` serves `assets/dashboard/index.html`, `codebase-map.json`, optional `diff-overlay.json`, and source excerpts over localhost.

The dashboard includes preset searches for common codebase questions such as entry points, prompt flow, commands, tools, permissions, messages, config, and tests. Selecting a node shows responsibility, evidence, risks, source excerpt, relationships, and copyable follow-up commands. Presets are a navigation aid; verify final claims against source files.
