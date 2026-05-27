# Understand-Anything Analysis

Source inspected:

- Repository: `https://github.com/Lum1104/Understand-Anything`
- Commit: `1a16e4de615596d703cbf67f50ee2bb3f5ffde00`
- License observed in repository: MIT

This skill does not vendor the upstream plugin or copy its source files. It adapts the public architectural idea into a smaller Codex skill with original scripts and a local graph contract.

## What The Upstream Project Does Well

The useful core is a codebase comprehension loop:

1. Scan project files and classify languages, frameworks, and categories.
2. Extract structural facts such as files, functions, classes, imports, configs, docs, schemas, services, and endpoints.
3. Build a graph with nodes, edges, layers, and guided tours.
4. Use the graph for chat, focused explanation, diff impact, domain flow analysis, and onboarding.
5. Keep graph outputs in a dedicated hidden directory, with intermediate files separated from durable graph files.

The important engineering idea is not the visual dashboard. It is the durable intermediate representation that lets an agent ask smaller, targeted questions instead of repeatedly scanning the whole repository.

## What We Changed

- Collapsed multiple slash commands into one Codex skill.
- Replaced external plugin installation with local Python scripts.
- Kept deterministic scanning and graph validation as the first step.
- Added a semantic pack/annotation/merge layer so the graph can carry responsibility, evidence, confidence, risks, and language notes instead of acting only as a file map.
- Added a self-contained dashboard for graph navigation, source excerpts, diff overlay, and node-level follow-up actions.
- Made source verification mandatory before final claims.
- Kept the graph schema small enough for repo onboarding, review, and impact analysis.
- Avoided committing generated graph output by default.

## What We Intentionally Did Not Adopt

- No multi-agent mandatory pipeline. Dispatching many agents is expensive and fragile for small and medium repos.
- No broad language-parser runtime dependency. The scanner uses stdlib and conservative regex heuristics.
- No automatic commit hook. Auto-updating analysis artifacts can surprise users and pollute unrelated diffs.

## Practical Heuristics To Preserve

- Generate progress and counts for long scans.
- Prefer `git ls-files` for deterministic file enumeration.
- Separate generated graph output from intermediate scratch.
- Use a one-hop impact model for diffs first; widen only when evidence requires it.
- Treat graph layers as navigation hints, not architectural truth.
- Report unmapped files as stale-graph or unsupported-language evidence.
