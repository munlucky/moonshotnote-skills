#!/usr/bin/env python3
"""Validate a codebase-understanding graph."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_NODE_TYPES = {
    "file",
    "function",
    "class",
    "module",
    "config",
    "document",
    "service",
    "endpoint",
    "pipeline",
    "schema",
    "resource",
    "test",
}
ALLOWED_EDGE_TYPES = {
    "contains",
    "imports",
    "tested_by",
    "configures",
    "documents",
    "related",
}
ALLOWED_COMPLEXITY = {"simple", "moderate", "complex"}
REQUIRED_V2_NODE_FIELDS = {
    "summary",
    "responsibility",
    "evidence",
    "confidence",
    "layerReason",
    "riskHints",
    "languageNotes",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a codebase graph JSON file.")
    parser.add_argument("graph", help="Path to codebase-map.json.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable report.")
    return parser.parse_args()


def validate(graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if graph.get("kind") != "codebase":
        errors.append("root.kind must be 'codebase'")
    schema_version = graph.get("schemaVersion", 1)
    if not isinstance(schema_version, int) or schema_version < 1:
        errors.append("root.schemaVersion must be a positive integer")
    if not isinstance(graph.get("project"), dict):
        errors.append("root.project must be an object")
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    layers = graph.get("layers")
    if not isinstance(nodes, list):
        errors.append("root.nodes must be an array")
        nodes = []
    if not isinstance(edges, list):
        errors.append("root.edges must be an array")
        edges = []
    if not isinstance(layers, list):
        errors.append("root.layers must be an array")
        layers = []

    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"nodes[{index}] must be an object")
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            errors.append(f"nodes[{index}].id is required")
            continue
        if node_id in node_ids:
            errors.append(f"duplicate node id: {node_id}")
        node_ids.add(node_id)
        node_type = node.get("type")
        if node_type not in ALLOWED_NODE_TYPES:
            errors.append(f"{node_id}: invalid node type {node_type!r}")
        if not isinstance(node.get("name"), str) or not node.get("name"):
            errors.append(f"{node_id}: name is required")
        if node.get("complexity") not in ALLOWED_COMPLEXITY:
            errors.append(f"{node_id}: invalid complexity {node.get('complexity')!r}")
        if not isinstance(node.get("tags", []), list):
            errors.append(f"{node_id}: tags must be an array")
        if schema_version >= 2:
            missing = sorted(field for field in REQUIRED_V2_NODE_FIELDS if field not in node)
            if missing:
                errors.append(f"{node_id}: missing v2 field(s): {', '.join(missing)}")
            confidence = node.get("confidence")
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                errors.append(f"{node_id}: confidence must be between 0 and 1")
            if not isinstance(node.get("evidence", []), list):
                errors.append(f"{node_id}: evidence must be an array")
            if not isinstance(node.get("riskHints", []), list):
                errors.append(f"{node_id}: riskHints must be an array")

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"edges[{index}] must be an object")
            continue
        source = edge.get("source")
        target = edge.get("target")
        edge_type = edge.get("type")
        if source not in node_ids:
            errors.append(f"edges[{index}].source missing node: {source!r}")
        if target not in node_ids:
            errors.append(f"edges[{index}].target missing node: {target!r}")
        if edge_type not in ALLOWED_EDGE_TYPES:
            errors.append(f"edges[{index}]: invalid edge type {edge_type!r}")
        weight = edge.get("weight", 1.0)
        if not isinstance(weight, (int, float)) or weight < 0 or weight > 1:
            errors.append(f"edges[{index}]: weight must be between 0 and 1")

    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            errors.append(f"layers[{index}] must be an object")
            continue
        if not isinstance(layer.get("id"), str) or not layer.get("id"):
            errors.append(f"layers[{index}].id is required")
        node_list = layer.get("nodeIds")
        if not isinstance(node_list, list):
            errors.append(f"layers[{index}].nodeIds must be an array")
            continue
        for node_id in node_list:
            if node_id not in node_ids:
                errors.append(f"layers[{index}] references missing node: {node_id!r}")

    return errors


def main() -> int:
    args = parse_args()
    graph_path = Path(args.graph)
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"failed to read graph: {exc}", file=sys.stderr)
        return 1

    errors = validate(graph)
    report = {
        "ok": not errors,
        "errors": errors,
        "schemaVersion": graph.get("schemaVersion", 1),
        "nodes": len(graph.get("nodes", [])) if isinstance(graph.get("nodes"), list) else 0,
        "edges": len(graph.get("edges", [])) if isinstance(graph.get("edges"), list) else 0,
        "layers": len(graph.get("layers", [])) if isinstance(graph.get("layers"), list) else 0,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif errors:
        print("Graph validation failed:")
        for error in errors:
            print(f"- {error}")
    else:
        print(
            f"Graph validation passed: {report['nodes']} nodes, "
            f"{report['edges']} edges, {report['layers']} layers."
        )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
