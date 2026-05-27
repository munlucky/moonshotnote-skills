#!/usr/bin/env python3
"""Query a codebase graph or map changed files to impacted nodes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from graph_utils import configure_stdout, diff_nodes, format_node, load_graph, query_nodes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query a codebase graph.")
    parser.add_argument("graph", help="Path to codebase-map.json.")
    parser.add_argument("--q", "--query", dest="query", help="Keyword query.")
    parser.add_argument(
        "--changed-file",
        action="append",
        default=[],
        help="Changed repository-relative file path. Repeat for multiple files.",
    )
    parser.add_argument("--limit", type=int, default=12, help="Maximum direct query matches.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    return parser.parse_args()


def emit_markdown(result: dict[str, Any], mode: str) -> str:
    lines: list[str] = []
    project = result.get("project", {})
    lines.append(f"# {mode}: {project.get('name', 'codebase')}")
    lines.append("")

    lines.append("## Direct Nodes")
    if not result["directNodes"]:
        lines.append("")
        lines.append("No direct graph nodes matched.")
    else:
        lines.append("")
        for node in result["directNodes"]:
            lines.append(format_node(node))
    lines.append("")

    lines.append("## Affected Nodes")
    if not result["affectedNodes"]:
        lines.append("")
        lines.append("No one-hop affected nodes found.")
    else:
        lines.append("")
        for node in result["affectedNodes"][:30]:
            lines.append(format_node(node))
    lines.append("")

    lines.append("## Layers")
    if not result["layers"]:
        lines.append("")
        lines.append("No layer context found.")
    else:
        lines.append("")
        for layer in result["layers"]:
            lines.append(f"- **{layer.get('name')}**: {layer.get('description')}")
    lines.append("")

    if result["unmappedFiles"]:
        lines.append("## Unmapped Files")
        lines.append("")
        for file_path in result["unmappedFiles"]:
            lines.append(f"- `{file_path}`")
        lines.append("")

    lines.append("## Relevant Edges")
    if not result["edges"]:
        lines.append("")
        lines.append("No relevant edges found.")
    else:
        lines.append("")
        for edge in result["edges"][:40]:
            lines.append(
                f"- `{edge.get('source')}` --{edge.get('type')}--> `{edge.get('target')}`"
            )
    return "\n".join(lines)


def main() -> int:
    configure_stdout()
    args = parse_args()
    graph = load_graph(Path(args.graph))
    if args.changed_file:
        result = diff_nodes(graph, args.changed_file)
        mode = "Diff Impact"
    elif args.query:
        result = query_nodes(graph, args.query, args.limit)
        mode = "Graph Query"
    else:
        raise SystemExit("Provide --q or at least one --changed-file.")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(emit_markdown(result, mode))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
