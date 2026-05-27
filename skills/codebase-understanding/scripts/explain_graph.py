#!/usr/bin/env python3
"""Build a focused explanation context for a file, function, class, or node."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from graph_utils import configure_stdout, evidence_lines, explain_context, format_node, load_graph, source_excerpt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Explain a graph component.")
    parser.add_argument("graph", help="Path to codebase-map.json.")
    parser.add_argument("target", help="File path, node id, node name, or file:path:symbol.")
    parser.add_argument("--root", help="Source root for optional source excerpt.")
    parser.add_argument("--source-lines", type=int, default=80, help="Maximum source lines to include.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    return parser.parse_args()


def emit_markdown(ctx: dict, root: str | None, source_lines: int) -> str:
    project = ctx.get("project", {})
    target = ctx.get("target")
    target_node = ctx.get("targetNode")
    lines: list[str] = [f"# Component Explanation Context: {project.get('name', 'codebase')}", ""]

    if not target_node:
        lines.extend(
            [
                f"Target `{target}` was not found in the graph.",
                "",
                "Refresh the graph or check the exact repository-relative path.",
            ]
        )
        return "\n".join(lines)

    lines.append("## Target")
    lines.append(format_node(target_node))
    if target_node.get("responsibility"):
        lines.append(f"- Responsibility: {target_node.get('responsibility')}")
    if target_node.get("layerReason"):
        lines.append(f"- Layer reason: {target_node.get('layerReason')}")
    if target_node.get("languageNotes"):
        lines.append(f"- Language notes: {target_node.get('languageNotes')}")
    if target_node.get("riskHints"):
        lines.append("- Risk hints:")
        for hint in target_node.get("riskHints", [])[:8]:
            lines.append(f"  - {hint}")
    lines.append("")

    layer = ctx.get("layer")
    if layer:
        lines.append("## Layer")
        lines.append(f"- **{layer.get('name')}**: {layer.get('description')}")
        lines.append("")

    child_nodes = ctx.get("childNodes", [])
    if child_nodes:
        lines.append("## Internal Nodes")
        for node in child_nodes[:40]:
            lines.append(format_node(node))
        lines.append("")

    connected_nodes = ctx.get("connectedNodes", [])
    if connected_nodes:
        lines.append("## Connected Nodes")
        for node in connected_nodes[:40]:
            lines.append(format_node(node))
        lines.append("")

    edges = [edge for edge in ctx.get("edges", []) if edge.get("type") != "contains"]
    if edges:
        lines.append("## Relationships")
        for edge in edges[:60]:
            lines.append(f"- `{edge.get('source')}` --{edge.get('type')}--> `{edge.get('target')}`")
        lines.append("")

    evidence = evidence_lines(target_node)
    if evidence:
        lines.append("## Evidence")
        for item in evidence:
            lines.append(f"- {item}")
        lines.append("")

    excerpt = source_excerpt(root, target_node, source_lines)
    if excerpt:
        lines.append("## Source Excerpt")
        lines.append("")
        lines.append("```text")
        lines.append(excerpt)
        lines.append("```")
        lines.append("")

    lines.append("## Answer Instructions")
    lines.append("Explain what this component does, why it exists, where data flows in/out, what depends on it, what it depends on, and what to inspect before changing it. Cite the evidence paths above and the source excerpt when making concrete claims.")
    return "\n".join(lines)


def main() -> int:
    configure_stdout()
    args = parse_args()
    graph = load_graph(Path(args.graph))
    ctx = explain_context(graph, args.target)
    if args.json:
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
    else:
        print(emit_markdown(ctx, args.root, args.source_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
