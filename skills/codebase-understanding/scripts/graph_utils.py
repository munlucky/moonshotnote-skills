#!/usr/bin/env python3
"""Shared helpers for codebase graph consumer scripts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def load_graph(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def norm_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def node_map(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {node["id"]: node for node in graph.get("nodes", []) if isinstance(node, dict)}


def searchable_text(node: dict[str, Any]) -> str:
    pieces = [
        node.get("id", ""),
        node.get("type", ""),
        node.get("name", ""),
        node.get("filePath", ""),
        node.get("summary", ""),
        node.get("responsibility", ""),
        node.get("layerReason", ""),
        node.get("languageNotes", ""),
        " ".join(node.get("riskHints", [])),
        " ".join(node.get("tags", [])),
    ]
    return "\n".join(str(piece) for piece in pieces).lower()


def query_nodes(graph: dict[str, Any], query: str, limit: int = 12) -> dict[str, Any]:
    terms = [term.lower() for term in query.split() if term.strip()]
    scored: list[tuple[int, dict[str, Any]]] = []
    for node in graph.get("nodes", []):
        text = searchable_text(node)
        score = sum(1 for term in terms if term in text)
        if not score:
            continue
        if any(term in str(node.get("name", "")).lower() for term in terms):
            score += 2
        if any(term in str(node.get("filePath", "")).lower() for term in terms):
            score += 2
        scored.append((score, node))

    scored.sort(key=lambda item: (-item[0], item[1].get("id", "")))
    direct = [node for _, node in scored[:limit]]
    return expand_context(graph, {node["id"] for node in direct}, direct, [])


def find_target_node(graph: dict[str, Any], target: str) -> dict[str, Any] | None:
    normalized_target = norm_path(target)
    nodes = graph.get("nodes", [])

    if ":" in normalized_target and "://" not in normalized_target:
        file_path, symbol = normalized_target.rsplit(":", 1)
        for node in nodes:
            if norm_path(str(node.get("filePath", ""))) == file_path and node.get("name") == symbol:
                return node

    for node in nodes:
        if node.get("id") == target:
            return node
        if norm_path(str(node.get("filePath", ""))) == normalized_target and node.get("type") == "file":
            return node

    for node in nodes:
        if node.get("name") == target:
            return node
    return None


def diff_nodes(graph: dict[str, Any], changed_files: list[str]) -> dict[str, Any]:
    normalized = {norm_path(path) for path in changed_files}
    by_id = node_map(graph)
    changed_ids: set[str] = set()
    unmapped = set(normalized)

    for node in graph.get("nodes", []):
        file_path = norm_path(str(node.get("filePath", "")))
        if file_path in normalized:
            changed_ids.add(node["id"])
            unmapped.discard(file_path)

    for edge in graph.get("edges", []):
        if edge.get("type") == "contains" and edge.get("source") in changed_ids:
            changed_ids.add(edge.get("target", ""))

    direct = [by_id[node_id] for node_id in sorted(changed_ids) if node_id in by_id]
    return expand_context(graph, changed_ids, direct, sorted(unmapped))


def explain_context(graph: dict[str, Any], target: str) -> dict[str, Any]:
    target_node = find_target_node(graph, target)
    if not target_node:
        return {
            "project": graph.get("project", {}),
            "target": target,
            "targetNode": None,
            "childNodes": [],
            "connectedNodes": [],
            "edges": [],
            "layer": None,
        }

    by_id = node_map(graph)
    target_id = target_node["id"]
    child_ids = {
        edge.get("target")
        for edge in graph.get("edges", [])
        if edge.get("source") == target_id and edge.get("type") == "contains"
    }
    seed_ids = {target_id, *{node_id for node_id in child_ids if isinstance(node_id, str)}}
    edges = []
    connected_ids: set[str] = set()
    for edge in graph.get("edges", []):
        source = edge.get("source")
        target_id_edge = edge.get("target")
        if source in seed_ids or target_id_edge in seed_ids:
            edges.append(edge)
            if isinstance(source, str) and source not in seed_ids:
                connected_ids.add(source)
            if isinstance(target_id_edge, str) and target_id_edge not in seed_ids:
                connected_ids.add(target_id_edge)

    layer = None
    for item in graph.get("layers", []):
        if target_node["id"] in item.get("nodeIds", []):
            layer = item
            break

    return {
        "project": graph.get("project", {}),
        "target": target,
        "targetNode": target_node,
        "childNodes": [by_id[node_id] for node_id in sorted(child_ids) if node_id in by_id],
        "connectedNodes": [by_id[node_id] for node_id in sorted(connected_ids) if node_id in by_id],
        "edges": edges,
        "layer": layer,
    }


def expand_context(
    graph: dict[str, Any],
    seed_ids: set[str],
    direct: list[dict[str, Any]],
    unmapped_files: list[str],
) -> dict[str, Any]:
    by_id = node_map(graph)
    neighbor_ids: set[str] = set()
    relevant_edges = []
    for edge in graph.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")
        if source in seed_ids or target in seed_ids:
            relevant_edges.append(edge)
            if isinstance(source, str) and source not in seed_ids:
                neighbor_ids.add(source)
            if isinstance(target, str) and target not in seed_ids:
                neighbor_ids.add(target)

    direct_ids = {node["id"] for node in direct}
    affected = [
        by_id[node_id]
        for node_id in sorted(neighbor_ids - direct_ids)
        if node_id in by_id
    ]
    all_ids = direct_ids | {node["id"] for node in affected}
    layers = [
        layer
        for layer in graph.get("layers", [])
        if any(node_id in all_ids for node_id in layer.get("nodeIds", []))
    ]
    return {
        "project": graph.get("project", {}),
        "directNodes": direct,
        "affectedNodes": affected,
        "edges": relevant_edges,
        "layers": layers,
        "unmappedFiles": unmapped_files,
    }


def format_node(node: dict[str, Any]) -> str:
    file_part = f" `{node.get('filePath')}`" if node.get("filePath") else ""
    line_part = f" lines {node.get('lineRange')}" if node.get("lineRange") else ""
    confidence = node.get("confidence")
    confidence_part = f" confidence {confidence:.2f}" if isinstance(confidence, (int, float)) else ""
    return (
        f"- **{node.get('name')}** ({node.get('type')}){file_part}{line_part}: "
        f"{node.get('summary', '')}{confidence_part}"
    )


def short_node(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": node.get("id"),
        "type": node.get("type"),
        "name": node.get("name"),
        "filePath": node.get("filePath"),
        "lineRange": node.get("lineRange"),
        "summary": node.get("summary"),
        "responsibility": node.get("responsibility"),
        "confidence": node.get("confidence"),
        "riskHints": node.get("riskHints", []),
        "evidence": node.get("evidence", []),
        "complexity": node.get("complexity"),
        "tags": node.get("tags", []),
    }


def source_excerpt(root: Path | str | None, node: dict[str, Any] | None, max_lines: int = 80) -> str | None:
    if not root or not node or not node.get("filePath"):
        return None
    path = Path(root) / str(node["filePath"])
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    start = 1
    end = min(len(lines), max_lines)
    evidence = node.get("evidence") if isinstance(node.get("evidence"), list) else []
    for item in evidence:
        if not isinstance(item, dict) or item.get("filePath") != node.get("filePath"):
            continue
        line_range = item.get("lineRange")
        if isinstance(line_range, list) and len(line_range) == 2:
            start = max(1, int(line_range[0]) - 8)
            end = min(len(lines), int(line_range[1]) + 24)
            break
    if node.get("lineRange"):
        line_range = node["lineRange"]
        start = max(1, int(line_range[0]) - 8)
        end = min(len(lines), int(line_range[1]) + 24)
    selected = lines[start - 1 : min(end, start + max_lines - 1)]
    return "\n".join(f"{idx}: {line}" for idx, line in enumerate(selected, start=start))


def evidence_lines(node: dict[str, Any]) -> list[str]:
    evidence = node.get("evidence", [])
    if not isinstance(evidence, list):
        return []
    lines = []
    for item in evidence[:5]:
        if not isinstance(item, dict):
            continue
        file_path = item.get("filePath")
        line_range = item.get("lineRange")
        if file_path and isinstance(line_range, list) and len(line_range) == 2:
            lines.append(f"`{file_path}:{line_range[0]}-{line_range[1]}`")
        elif file_path:
            lines.append(f"`{file_path}`")
    return lines
