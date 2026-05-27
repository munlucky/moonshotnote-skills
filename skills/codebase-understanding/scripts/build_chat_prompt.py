#!/usr/bin/env python3
"""Build an LLM-ready prompt from graph query context."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from graph_utils import configure_stdout, evidence_lines, format_node, load_graph, query_nodes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a codebase chat prompt from graph context.")
    parser.add_argument("graph", help="Path to codebase-map.json.")
    parser.add_argument("--q", "--query", required=True, dest="query", help="User question.")
    parser.add_argument("--limit", type=int, default=12, help="Maximum direct graph matches.")
    parser.add_argument("--json", action="store_true", help="Emit context JSON instead of prompt Markdown.")
    return parser.parse_args()


def emit_prompt(ctx: dict, query: str) -> str:
    project = ctx.get("project", {})
    lines: list[str] = [
        "You are answering a question about a software repository.",
        "Use the graph context below as an index, then verify important claims against source evidence before finalizing.",
        "Answer in Korean unless the user explicitly requests another language.",
        "Every concrete claim should cite file paths or line ranges from the Evidence section when available.",
        "",
        f"# Project: {project.get('name', 'codebase')}",
        f"- Languages: {', '.join(project.get('languages', []))}",
        f"- Framework hints: {', '.join(project.get('frameworkHints', []))}",
        f"- Git commit: {project.get('gitCommitHash', 'unknown')}",
        f"- Semantic mode: {project.get('analysis', {}).get('semanticMode', 'unknown')}",
        "",
        "## Relevant Layers",
    ]

    if ctx.get("layers"):
        for layer in ctx["layers"]:
            lines.append(f"- **{layer.get('name')}**: {layer.get('description')}")
    else:
        lines.append("- No layer context found.")

    lines.extend(["", "## Direct Matches"])
    if ctx.get("directNodes"):
        for node in ctx["directNodes"]:
            lines.append(format_node(node))
            if node.get("responsibility"):
                lines.append(f"  - Responsibility: {node.get('responsibility')}")
            if node.get("riskHints"):
                lines.append(f"  - Risk hints: {'; '.join(node.get('riskHints', [])[:3])}")
    else:
        lines.append("- No direct matches.")

    lines.extend(["", "## One-hop Neighbors"])
    if ctx.get("affectedNodes"):
        for node in ctx["affectedNodes"][:40]:
            lines.append(format_node(node))
    else:
        lines.append("- No one-hop neighbors.")

    evidence = []
    for node in [*ctx.get("directNodes", []), *ctx.get("affectedNodes", [])[:12]]:
        evidence.extend(evidence_lines(node))
    lines.extend(["", "## Evidence"])
    if evidence:
        for item in list(dict.fromkeys(evidence))[:30]:
            lines.append(f"- {item}")
    else:
        lines.append("- No explicit evidence ranges available; read matching files directly.")

    lines.extend(["", "## Relationships"])
    if ctx.get("edges"):
        for edge in ctx["edges"][:60]:
            desc = f": {edge.get('description')}" if edge.get("description") else ""
            lines.append(f"- `{edge.get('source')}` --{edge.get('type')}--> `{edge.get('target')}`{desc}")
    else:
        lines.append("- No relevant edges.")

    lines.extend(
        [
            "",
            "## Answer Shape",
            "1. Direct answer",
            "2. Supporting files/functions",
            "3. Important dependencies or risks",
            "4. What to inspect next",
            "",
            "## User Question",
            query,
        ]
    )
    return "\n".join(lines)


def main() -> int:
    configure_stdout()
    args = parse_args()
    graph = load_graph(Path(args.graph))
    ctx = query_nodes(graph, args.query, args.limit)
    if args.json:
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
    else:
        print(emit_prompt(ctx, args.query))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
