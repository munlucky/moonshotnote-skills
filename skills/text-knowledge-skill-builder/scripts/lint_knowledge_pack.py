#!/usr/bin/env python3
"""Lint a public knowledge pack for schema, provenance, and graph consistency."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


NODE_FIELDS = {"id", "type", "name", "summary", "aliases", "source_refs", "public_safe"}
EDGE_FIELDS = {"source", "target", "type", "summary", "source_refs", "public_safe"}
CHUNK_FIELDS = {"id", "title", "summary", "source_refs", "keywords", "public_safe"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def require_fields(kind: str, ident: str, item: dict, fields: set[str]) -> None:
    missing = sorted(fields - set(item))
    if missing:
        raise ValueError(f"{kind} {ident}: missing fields {missing}")


def require_public(kind: str, ident: str, item: dict, max_summary_chars: int) -> None:
    if item.get("public_safe") is not True:
        raise ValueError(f"{kind} {ident}: public_safe must be true")
    if not isinstance(item.get("source_refs"), list) or not item["source_refs"]:
        raise ValueError(f"{kind} {ident}: source_refs must be a non-empty list")
    summary = item.get("summary", "")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError(f"{kind} {ident}: summary must be non-empty")
    if len(summary) > max_summary_chars:
        raise ValueError(f"{kind} {ident}: summary exceeds {max_summary_chars} chars")


def lint(references_dir: Path, max_summary_chars: int) -> None:
    required_paths = [
        references_dir / "ontology.yaml",
        references_dir / "graph_manifest.json",
        references_dir / "nodes.jsonl",
        references_dir / "edges.jsonl",
        references_dir / "chunks.jsonl",
    ]
    missing = [str(path) for path in required_paths if not path.is_file()]
    if missing:
        raise ValueError("missing required files: " + ", ".join(missing))

    manifest = load_json(references_dir / "graph_manifest.json")
    if manifest.get("public_sanitized") is not True:
        raise ValueError("graph_manifest.json: public_sanitized must be true")

    nodes = load_jsonl(references_dir / "nodes.jsonl")
    edges = load_jsonl(references_dir / "edges.jsonl")
    chunks = load_jsonl(references_dir / "chunks.jsonl")
    node_ids: set[str] = set()
    connected: set[str] = set()

    for node in nodes:
        ident = node.get("id", "<missing>")
        require_fields("node", ident, node, NODE_FIELDS)
        if ident in node_ids:
            raise ValueError(f"duplicate node id: {ident}")
        node_ids.add(ident)
        if not isinstance(node.get("aliases"), list):
            raise ValueError(f"node {ident}: aliases must be a list")
        require_public("node", ident, node, max_summary_chars)

    for edge in edges:
        ident = f"{edge.get('source', '?')}->{edge.get('target', '?')}"
        require_fields("edge", ident, edge, EDGE_FIELDS)
        if edge["source"] not in node_ids:
            raise ValueError(f"edge {ident}: unknown source")
        if edge["target"] not in node_ids:
            raise ValueError(f"edge {ident}: unknown target")
        connected.update([edge["source"], edge["target"]])
        require_public("edge", ident, edge, max_summary_chars)

    for chunk in chunks:
        ident = chunk.get("id", "<missing>")
        require_fields("chunk", ident, chunk, CHUNK_FIELDS)
        if not isinstance(chunk.get("keywords"), list) or not chunk["keywords"]:
            raise ValueError(f"chunk {ident}: keywords must be a non-empty list")
        require_public("chunk", ident, chunk, max_summary_chars)

    orphans = sorted(node_ids - connected)
    if orphans:
        raise ValueError(f"orphan nodes: {orphans}")

    counts = manifest.get("counts", {})
    expected = {"nodes": len(nodes), "edges": len(edges), "chunks": len(chunks)}
    if counts != expected:
        raise ValueError(f"manifest counts mismatch: expected {expected}, got {counts}")

    print(f"Knowledge pack valid: {len(nodes)} nodes, {len(edges)} edges, {len(chunks)} chunks")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("references_dir")
    parser.add_argument("--max-summary-chars", type=int, default=600)
    args = parser.parse_args()
    try:
        lint(Path(args.references_dir), args.max_summary_chars)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
