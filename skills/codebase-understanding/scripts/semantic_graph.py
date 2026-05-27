#!/usr/bin/env python3
"""Generate and merge semantic annotations for a codebase graph.

The script keeps LLM execution outside the deterministic scanner. It can:

- write review packs that Codex or another LLM can use for deeper analysis
- create conservative heuristic annotations immediately
- merge annotations back into the graph schema v2 fields
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from graph_utils import configure_stdout, load_graph, node_map


VERSION = "0.2.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or merge semantic codebase graph annotations.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("pack", "annotate", "run"):
        item = subparsers.add_parser(name)
        item.add_argument("graph", help="Path to codebase-map.json.")
        item.add_argument("--root", required=True, help="Repository root for source excerpts.")
        item.add_argument("--limit", type=int, default=240, help="Maximum file nodes to process.")
        item.add_argument("--excerpt-lines", type=int, default=80)
        if name in {"pack", "run"}:
            item.add_argument("--packs-dir", required=True, help="Directory to write semantic pack JSONL files.")
        if name in {"annotate", "run"}:
            item.add_argument("--annotations-out", required=True, help="Output semantic annotations JSON.")
        if name == "run":
            item.add_argument("--out", required=True, help="Output merged graph path.")

    merge = subparsers.add_parser("merge")
    merge.add_argument("graph", help="Path to codebase-map.json.")
    merge.add_argument("--annotations", required=True, help="Annotations JSON produced by annotate or LLM review.")
    merge.add_argument("--out", required=True, help="Output merged graph path.")

    return parser.parse_args()


def file_nodes(graph: dict[str, Any]) -> list[dict[str, Any]]:
    allowed = {"file", "config", "document", "schema", "resource", "pipeline", "test"}
    nodes = [node for node in graph.get("nodes", []) if node.get("type") in allowed and node.get("filePath")]
    return sorted(nodes, key=priority_key)


def priority_key(node: dict[str, Any]) -> tuple[int, int, str]:
    path = str(node.get("filePath", ""))
    name = Path(path).name.lower()
    complexity_rank = {"complex": 0, "moderate": 1, "simple": 2}.get(str(node.get("complexity", "")), 3)
    entry_rank = 0 if name in {"main.ts", "main.tsx", "main.py", "index.ts", "index.tsx", "app.tsx", "server.ts", "cli.ts", "readme.md", "agents.md"} else 1
    return (entry_rank, complexity_rank, path)


def source_excerpt(root: Path, path: str, max_lines: int) -> dict[str, Any]:
    source = root / path
    try:
        lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {"filePath": path, "lineRange": None, "text": ""}
    end = min(len(lines), max_lines)
    return {
        "filePath": path,
        "lineRange": [1, end] if end else [1, 1],
        "text": "\n".join(f"{idx}: {line}" for idx, line in enumerate(lines[:end], start=1)),
    }


def inbound_outbound_counts(graph: dict[str, Any], node_id: str) -> tuple[int, int]:
    incoming = 0
    outgoing = 0
    for edge in graph.get("edges", []):
        if edge.get("target") == node_id:
            incoming += 1
        if edge.get("source") == node_id:
            outgoing += 1
    return incoming, outgoing


def child_symbols(graph: dict[str, Any], node_id: str) -> list[dict[str, Any]]:
    by_id = node_map(graph)
    symbols: list[dict[str, Any]] = []
    for edge in graph.get("edges", []):
        if edge.get("source") == node_id and edge.get("type") == "contains":
            child = by_id.get(str(edge.get("target")))
            if child:
                symbols.append(child)
    return symbols


def write_packs(graph: dict[str, Any], root: Path, packs_dir: Path, limit: int, excerpt_lines: int) -> dict[str, Any]:
    packs_dir.mkdir(parents=True, exist_ok=True)
    nodes = file_nodes(graph)[:limit]
    pack_path = packs_dir / "semantic-pack-0001.jsonl"
    with pack_path.open("w", encoding="utf-8", newline="\n") as handle:
        for node in nodes:
            incoming, outgoing = inbound_outbound_counts(graph, node["id"])
            symbols = child_symbols(graph, node["id"])[:40]
            item = {
                "nodeId": node["id"],
                "filePath": node.get("filePath"),
                "languageNotes": node.get("languageNotes"),
                "summarySeed": node.get("summary"),
                "responsibilitySeed": node.get("responsibility"),
                "metrics": node.get("metrics", {}),
                "complexity": node.get("complexity"),
                "tags": node.get("tags", []),
                "dependencyCounts": {"incoming": incoming, "outgoing": outgoing},
                "symbols": [
                    {
                        "name": symbol.get("name"),
                        "type": symbol.get("type"),
                        "lineRange": symbol.get("lineRange"),
                        "summary": symbol.get("summary"),
                    }
                    for symbol in symbols
                ],
                "sourceExcerpt": source_excerpt(root, str(node.get("filePath")), excerpt_lines),
                "instruction": (
                    "Return a compact JSON annotation with summary, responsibility, tags, "
                    "layerReason, riskHints, languageNotes, confidence, and evidence. "
                    "Do not invent behavior not supported by the excerpt or graph facts."
                ),
            }
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    return {"packs": [str(pack_path)], "items": len(nodes)}


def infer_semantic_annotation(graph: dict[str, Any], root: Path, node: dict[str, Any], excerpt_lines: int) -> dict[str, Any]:
    path = str(node.get("filePath"))
    excerpt = source_excerpt(root, path, excerpt_lines)
    text = excerpt.get("text", "")
    symbols = child_symbols(graph, node["id"])
    incoming, outgoing = inbound_outbound_counts(graph, node["id"])
    comment_hint = first_comment_or_heading(text)
    symbol_hint = ", ".join(symbol.get("name", "") for symbol in symbols[:6] if symbol.get("name"))
    tags = set(str(tag) for tag in node.get("tags", []))
    tags.update(path_tags(path))
    risk_hints = list(node.get("riskHints", []))
    if incoming > 8:
        risk_hints.append(f"many incoming graph edges ({incoming}); changing this can affect several callers")
    if outgoing > 12:
        risk_hints.append(f"many outgoing graph edges ({outgoing}); verify dependency contracts")
    if not symbols and node.get("type") == "file" and node.get("metrics", {}).get("lines", 0) > 120:
        risk_hints.append("large file with no detected symbols; parser may have missed important structure")

    summary = str(node.get("summary", ""))
    if comment_hint:
        summary = f"{summary}. Source hint: {comment_hint}"
    responsibility = str(node.get("responsibility", ""))
    if symbol_hint:
        responsibility = f"{responsibility} Primary detected symbols: {symbol_hint}."

    evidence = list(node.get("evidence", []))
    if excerpt.get("lineRange"):
        evidence = [{"kind": "source-excerpt", "filePath": path, "lineRange": excerpt["lineRange"]}]

    return {
        "nodeId": node["id"],
        "summary": summary,
        "responsibility": responsibility,
        "tags": sorted(tags),
        "layerReason": node.get("layerReason", ""),
        "riskHints": dedupe(risk_hints),
        "languageNotes": semantic_language_notes(node, incoming, outgoing),
        "confidence": min(0.86, float(node.get("confidence", 0.55)) + (0.08 if comment_hint else 0.02)),
        "evidence": evidence,
        "semanticMode": "heuristic",
    }


def first_comment_or_heading(numbered_text: str) -> str:
    for raw in numbered_text.splitlines()[:80]:
        line = re.sub(r"^\d+:\s*", "", raw).strip()
        if not line:
            continue
        if line.startswith("#!"):
            continue
        if line.startswith("#"):
            return line.lstrip("# ").strip()[:180]
        if line.startswith(("//", "/*", "*", '"""', "'''")):
            cleaned = line.strip("/ *\"'")
            if cleaned:
                return cleaned[:180]
    return ""


def path_tags(path: str) -> set[str]:
    lower = path.lower()
    tags: set[str] = set()
    for token in ("auth", "permission", "config", "prompt", "command", "tool", "message", "query", "server", "client", "test"):
        if token in lower:
            tags.add(token)
    return tags


def semantic_language_notes(node: dict[str, Any], incoming: int, outgoing: int) -> str:
    base = str(node.get("languageNotes", ""))
    graph_note = f"Graph degree: {incoming} incoming, {outgoing} outgoing."
    return f"{base} {graph_note}".strip()


def dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def write_annotations(graph: dict[str, Any], root: Path, annotations_out: Path, limit: int, excerpt_lines: int) -> dict[str, Any]:
    nodes = file_nodes(graph)[:limit]
    annotations = [infer_semantic_annotation(graph, root, node, excerpt_lines) for node in nodes]
    payload = {
        "version": VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "mode": "heuristic",
        "coverage": {"annotatedNodes": len(annotations), "candidateFileNodes": len(file_nodes(graph))},
        "annotations": annotations,
    }
    annotations_out.parent.mkdir(parents=True, exist_ok=True)
    annotations_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def merge_annotations(graph: dict[str, Any], annotations: dict[str, Any]) -> dict[str, Any]:
    by_id = node_map(graph)
    merged_count = 0
    for item in annotations.get("annotations", []):
        if not isinstance(item, dict):
            continue
        node = by_id.get(str(item.get("nodeId")))
        if not node:
            continue
        for field in ("summary", "responsibility", "evidence", "confidence", "layerReason", "riskHints", "languageNotes"):
            if field in item:
                node[field] = item[field]
        if isinstance(item.get("tags"), list):
            node["tags"] = sorted(set(str(tag) for tag in node.get("tags", []) + item["tags"]))
        node["semanticMode"] = item.get("semanticMode", annotations.get("mode", "external"))
        merged_count += 1

    project = graph.setdefault("project", {})
    analysis = project.setdefault("analysis", {})
    analysis["semanticMode"] = annotations.get("mode", "external")
    analysis["semanticAnalyzer"] = VERSION
    analysis["semanticGeneratedAt"] = annotations.get("generatedAt")
    analysis["semanticCoverage"] = {
        "annotatedNodes": merged_count,
        "totalNodes": len(graph.get("nodes", [])),
        "candidateFileNodes": annotations.get("coverage", {}).get("candidateFileNodes"),
    }
    graph["version"] = VERSION
    graph["schemaVersion"] = max(2, int(graph.get("schemaVersion", 1)))
    graph.setdefault("artifacts", {})["semanticAnnotations"] = annotations.get("path")
    return graph


def main() -> int:
    configure_stdout()
    args = parse_args()
    graph_path = Path(args.graph)
    graph = load_graph(graph_path)

    if args.command == "pack":
        result = write_packs(graph, Path(args.root).resolve(), Path(args.packs_dir), args.limit, args.excerpt_lines)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "annotate":
        payload = write_annotations(graph, Path(args.root).resolve(), Path(args.annotations_out), args.limit, args.excerpt_lines)
        print(
            f"Wrote {args.annotations_out} with {payload['coverage']['annotatedNodes']} heuristic annotations."
        )
        return 0

    if args.command == "merge":
        annotations_path = Path(args.annotations)
        annotations = load_graph(annotations_path)
        annotations["path"] = str(annotations_path)
        merged = merge_annotations(graph, annotations)
        out = Path(args.out)
        out.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Merged semantic annotations into {out}.")
        return 0

    if args.command == "run":
        packs = write_packs(graph, Path(args.root).resolve(), Path(args.packs_dir), args.limit, args.excerpt_lines)
        annotations_path = Path(args.annotations_out)
        annotations = write_annotations(graph, Path(args.root).resolve(), annotations_path, args.limit, args.excerpt_lines)
        annotations["path"] = str(annotations_path)
        merged = merge_annotations(graph, annotations)
        out = Path(args.out)
        out.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"Wrote semantic packs ({packs['items']} items), annotations "
            f"({annotations['coverage']['annotatedNodes']} nodes), and merged graph {out}."
        )
        return 0

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
