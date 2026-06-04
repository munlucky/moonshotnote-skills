---
name: codebase-understanding
description: Build and use a lightweight, queryable codebase knowledge graph for unfamiliar repositories. Use when Codex needs to onboard into a repo, explain architecture, map files/functions/classes/imports/layers, answer "how does this work" questions, assess git diff or PR blast radius, produce an onboarding path, or create a durable codebase map without installing a full external dashboard plugin.
---

# Codebase Understanding

## Contract

Use this skill to turn a repository into a compact code graph, then answer from that graph plus targeted source reads. The graph is an aid, not the source of truth: verify claims against current files before making edits or high-risk recommendations.

Default output language is Korean unless the user asks otherwise.

This is an agent-operated skill. Do not ask the user to run the bundled Python commands unless they explicitly want manual CLI usage. When the user invokes `$codebase-understanding`, asks to understand a repository, asks how code is structured, asks for onboarding, asks a broad flow question, asks for file/symbol explanation, asks for diff impact, or asks to open the dashboard, choose and run the appropriate script yourself.

The skill name is `codebase-understanding` because it describes the reusable capability. `moonshotnote-skills` is only the repository that distributes several skills; it is not the name of this individual skill.

## Agent Invocation Policy

1. Resolve the target repository.
   - If the user gives a path, use that path.
   - If no path is given, use the current Codex session's project/workspace root automatically. In a normal local session this is the shell current working directory. Do not ask the user for a path just because they omitted one.
   - If a subdirectory is given, let `understand_codebase.py` discover the repository root unless the user asks for a narrow subdirectory analysis.
2. Resolve the skill directory before running scripts.
   - Prefer the installed skill path when available: `${CODEX_HOME:-$HOME/.codex}/skills/codebase-understanding`.
   - If working from this repository, `skills/codebase-understanding` is also valid.
   - Prefer running the script by absolute path with the shell working directory set to the target repository. That lets the script's default `.` mean the current project.
   - If you run from the skill directory instead, pass the target repository as an absolute path.
3. Select the consumer mode from the user's intent.
   - Whole repo onboarding, "study this repo", or no specific question: run `onboard` after ensuring a graph exists.
   - Broad architecture or flow question: run `chat . "<question>"` from the target repository, or pass the absolute target repository if running elsewhere.
   - Specific file, class, function, symbol, or `file:line` request: run `explain . <target>` from the target repository.
   - Review, PR, changed file, or blast-radius request: run `diff .` with changed files from git or user input.
   - Learning plan or all-file study guide: run `study .`.
   - Visual exploration request: run `dashboard .`.
4. Ensure graph freshness.
   - If `.codebase-understanding/codebase-map.json` is missing, run the product-style analyze flow first.
   - If the repository has changed substantially or the user asks for a fresh map, run analyze again.
   - For quick follow-up questions, reuse the existing graph, then verify final claims against source files.
5. Answer in terms of the user's request, not in terms of internal scripts. Mention generated files or dashboard URLs only when useful.

## Default Workflow

Use the product-style entrypoint first when a repository needs a fresh graph. It mirrors the upstream user flow without commit hooks or auto-update:

```powershell
py -3 <skill-dir>\scripts\understand_codebase.py
```

```bash
python3 <skill-dir>/scripts/understand_codebase.py
```

Default behavior:

1. Detect the project root.
2. Scan files and save `.codebase-understanding/codebase-map.json`.
3. Generate `.codebase-understanding/semantic-packs/*.jsonl` and heuristic semantic annotations, then merge responsibility, evidence, confidence, risk hints, and language notes into the graph.
4. If git changed files are available, write `.codebase-understanding/diff-overlay.json`.
5. Open the dashboard unless `--no-dashboard` is passed.

Use these subcommands for the original consumer surfaces:

```powershell
py -3 scripts\understand_codebase.py chat <repo-root> "How does auth work?"
py -3 scripts\understand_codebase.py diff <repo-root> --changed-file src\auth.ts
py -3 scripts\understand_codebase.py explain <repo-root> src\auth.ts:login
py -3 scripts\understand_codebase.py onboard <repo-root>
py -3 scripts\understand_codebase.py study <repo-root>
py -3 scripts\understand_codebase.py semantic <repo-root>
py -3 scripts\understand_codebase.py dashboard <repo-root>
```

```bash
python3 scripts/understand_codebase.py chat <repo-root> "How does auth work?"
python3 scripts/understand_codebase.py diff <repo-root> --changed-file src/auth.ts
python3 scripts/understand_codebase.py explain <repo-root> src/auth.ts:login
python3 scripts/understand_codebase.py onboard <repo-root>
python3 scripts/understand_codebase.py study <repo-root>
python3 scripts/understand_codebase.py semantic <repo-root>
python3 scripts/understand_codebase.py dashboard <repo-root>
```

## Low-Level Workflow

Use individual scripts when automation needs one step only.

1. Resolve the repository root.
   - Prefer `git rev-parse --show-toplevel`.
   - If the user gives a subdirectory, let `scan_codebase.py` climb to the project root by default so package manifests and TypeScript configs are visible.
   - Use `--no-root-discovery` only when the user explicitly wants an isolated subdirectory graph.
   - If running inside a Git worktree, write graph outputs to the active working tree unless the user explicitly wants the main checkout.
   - Use the platform's Python launcher:
     - Windows: `py -3`
     - macOS/Linux: `python3`
2. Create or refresh the graph:

   ```powershell
   py -3 scripts\scan_codebase.py <repo-root> --out <repo-root>\.codebase-understanding\codebase-map.json
   ```

   ```bash
   python3 scripts/scan_codebase.py <repo-root> --out <repo-root>/.codebase-understanding/codebase-map.json
   ```

3. Validate the graph before relying on it:

   ```powershell
   py -3 scripts\validate_graph.py <repo-root>\.codebase-understanding\codebase-map.json
   ```

   ```bash
   python3 scripts/validate_graph.py <repo-root>/.codebase-understanding/codebase-map.json
   ```

4. Query only the relevant subgraph:

   ```powershell
   py -3 scripts\query_graph.py <repo-root>\.codebase-understanding\codebase-map.json --q "auth login token"
   ```

   ```bash
   python3 scripts/query_graph.py <repo-root>/.codebase-understanding/codebase-map.json --q "auth login token"
   ```

5. Use the consumer layer that matches the task:

   ```powershell
   py -3 scripts\explain_graph.py <graph> src\auth.ts --root <repo-root>
   py -3 scripts\build_chat_prompt.py <graph> --q "How does auth work?"
   py -3 scripts\semantic_graph.py run <graph> --root <repo-root> --packs-dir <repo-root>\.codebase-understanding\semantic-packs --annotations-out <repo-root>\.codebase-understanding\semantic-annotations.json --out <graph>
   py -3 scripts\write_diff_overlay.py <graph> --changed-file src\auth.ts --out <repo-root>\.codebase-understanding\diff-overlay.json
   py -3 scripts\serve_dashboard.py <graph> --diff-overlay <repo-root>\.codebase-understanding\diff-overlay.json
   ```

   ```bash
   python3 scripts/explain_graph.py <graph> src/auth.ts --root <repo-root>
   python3 scripts/build_chat_prompt.py <graph> --q "How does auth work?"
   python3 scripts/semantic_graph.py run <graph> --root <repo-root> --packs-dir <repo-root>/.codebase-understanding/semantic-packs --annotations-out <repo-root>/.codebase-understanding/semantic-annotations.json --out <graph>
   python3 scripts/write_diff_overlay.py <graph> --changed-file src/auth.ts --out <repo-root>/.codebase-understanding/diff-overlay.json
   python3 scripts/serve_dashboard.py <graph> --diff-overlay <repo-root>/.codebase-understanding/diff-overlay.json
   ```

6. Read the actual source files for the selected nodes before finalizing an explanation, review finding, or implementation plan.

## Task Modes

### Repository Onboarding

Run the scanner, query for entry points, layers, and high-complexity files, then produce:

- project purpose and runtime shape
- main entry points
- architectural layers and dependency direction
- important files to read first
- risky areas and missing evidence

### Component Explanation

Use `query_graph.py --q` with the file, function, class, feature, or domain term. Expand one hop through `imports`, `contains`, and `tested_by` edges. Then read the selected source file and explain:

- role in the system
- incoming and outgoing dependencies
- contained symbols
- layer placement
- edge cases or complexity drivers

For a ready explanation context, run:

```powershell
py -3 scripts\explain_graph.py <graph> src\auth.ts:login --root <repo-root>
```

```bash
python3 scripts/explain_graph.py <graph> src/auth.ts:login --root <repo-root>
```

### Chat Prompt

Use `build_chat_prompt.py` when a user asks a broad repository question. It compresses query matches, one-hop neighbors, layers, relationships, risks, and evidence into an LLM-ready prompt. Treat the prompt as context; still verify final answers against files.

### Semantic Pass

Use `understand_codebase.py semantic` or `semantic_graph.py run` after a scan when the graph feels like a file map instead of an analysis surface. The semantic pass writes review packs for deeper LLM analysis and merges conservative heuristic annotations into the graph immediately. If a later Codex pass reviews the packs, merge its JSON annotations with `semantic_graph.py merge`.

### Diff Impact

Get changed files first, then map them to graph nodes:

```powershell
git diff --name-only
py -3 scripts\query_graph.py <graph> --changed-file src\foo.py --changed-file src\bar.ts
py -3 scripts\write_diff_overlay.py <graph> --changed-file src\foo.py --out <repo-root>\.codebase-understanding\diff-overlay.json
```

```bash
git diff --name-only
python3 scripts/query_graph.py <graph> --changed-file src/foo.py --changed-file src/bar.ts
python3 scripts/write_diff_overlay.py <graph> --changed-file src/foo.py --out <repo-root>/.codebase-understanding/diff-overlay.json
```

Report:

- directly changed components
- affected one-hop neighbors
- affected layers
- unmapped files that require graph refresh
- test and review focus

### Dashboard

Use `serve_dashboard.py` to inspect the graph visually. The dashboard is self-contained HTML/JS and reads `/codebase-map.json` plus optional `/diff-overlay.json` from the local server.

```powershell
py -3 scripts\serve_dashboard.py <graph> --diff-overlay <diff-overlay>
```

```bash
python3 scripts/serve_dashboard.py <graph> --diff-overlay <diff-overlay>
```

### Onboarding Path

Use layers and `tour` data from the graph as the starting order, but override it with evidence from README, manifests, entry points, and source files. Prefer a short ordered reading path over a giant file inventory.

### Study Pack

Use `understand_codebase.py study` when the user wants to learn a whole repo, not just answer one question. It ranks file nodes by entrypoint signals, complexity, symbol count, graph degree, preset matches, and risk hints, then writes Markdown chapters under `.codebase-understanding/reports/study/`.

Useful options:

```powershell
py -3 scripts\understand_codebase.py study <repo-root> --limit 120
py -3 scripts\understand_codebase.py study <repo-root> --all --exclude generated
py -3 scripts\understand_codebase.py study <repo-root> --preset permissions --preset tools
```

```bash
python3 scripts/understand_codebase.py study <repo-root> --limit 120
python3 scripts/understand_codebase.py study <repo-root> --all --exclude generated
python3 scripts/understand_codebase.py study <repo-root> --preset permissions --preset tools
```

Read `00-overview.md` first, then work through the chapter files. Use `explain` for a confusing card and `chat` for a cross-file flow question.

## Design Rules

- Do not dump the whole graph into context. Query first, then read source.
- Treat generated summaries as lossy. Source files, manifests, tests, and runtime logs outrank the graph.
- Keep graph output under `.codebase-understanding/`; do not mix it with product source directories.
- Do not commit graph outputs unless the user asks for a durable repo artifact.
- For large monorepos, scan the relevant subdirectory first, then widen if the answer needs cross-boundary context.
- If the query asks about current runtime behavior, verify with tests, commands, logs, or application execution after graph analysis.
- TypeScript import resolution is heuristic. The scanner reads nearby `tsconfig.json` or `jsconfig.json` `baseUrl` and `paths`, but it does not run the TypeScript compiler.
- The scanner supports multiple nested `tsconfig.json` / `jsconfig.json` files, simple local `extends`, `baseUrl`, `paths`, and index/barrel-style import candidates. It still does not execute the TypeScript compiler.
- Paths in graph JSON are normalized to forward slashes so outputs can move between Windows and macOS/Linux tools.
- The bundled scripts use only Python standard library modules; no OS-specific package install is required.

## Resources

- `references/graph-schema.md`: JSON shape, node types, edge types, and query strategy.
- `references/upstream-analysis.md`: public-safe analysis of the Understand-Anything repository and the adaptation choices used here.
- `scripts/scan_codebase.py`: deterministic repository scanner and graph writer.
- `scripts/semantic_graph.py`: semantic pack writer, heuristic annotation generator, and graph merge helper.
- `scripts/understand_codebase.py`: default product-style entrypoint for analyze, dashboard, chat, diff, explain, onboard, semantic, and study flows.
- `scripts/query_graph.py`: keyword query and changed-file impact helper.
- `scripts/explain_graph.py`: focused explanation context builder for a file, symbol, or node.
- `scripts/build_chat_prompt.py`: LLM prompt builder from graph query context.
- `scripts/write_diff_overlay.py`: diff overlay writer for changed/affected node highlighting.
- `scripts/serve_dashboard.py`: local dashboard server.
- `scripts/validate_graph.py`: schema and graph consistency checks.
- `assets/dashboard/index.html`: self-contained graph dashboard.
