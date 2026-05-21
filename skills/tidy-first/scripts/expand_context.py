#!/usr/bin/env python3
"""Write a compact source pack from Tidy First graph query results."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TOKEN_RE = re.compile(r"[A-Za-z0-9_./-]+|[가-힣]+")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def tokens(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def score_text(query_tokens: list[str], text: str) -> int:
    lower = text.lower()
    return sum(3 if token in lower and len(token) > 2 else 1 if token in lower else 0 for token in query_tokens)


def format_refs(refs: list[dict]) -> str:
    parts = []
    for ref in refs:
        section = ref.get("section", "?")
        start, end = ref.get("lines", ["?", "?"])
        parts.append(f"ch{ref.get('chapter', '?')} {section} lines {start}-{end}")
    return "; ".join(parts)


def build_pack(query: str, limit: int) -> str:
    refs = Path(__file__).resolve().parents[1] / "references"
    nodes = load_jsonl(refs / "nodes.jsonl")
    edges = load_jsonl(refs / "edges.jsonl")
    chunks = load_jsonl(refs / "chunks.jsonl")
    query_tokens = tokens(query)

    scored_nodes = []
    for node in nodes:
        haystack = " ".join([node["id"], node["type"], node["name"], node["summary"], " ".join(node["aliases"])])
        score = score_text(query_tokens, haystack)
        if score:
            scored_nodes.append((score, node))
    scored_nodes.sort(key=lambda item: (-item[0], item[1]["name"]))
    selected_nodes = [node for _, node in scored_nodes[:limit]]
    selected_ids = {node["id"] for node in selected_nodes}

    selected_edges = [
        edge
        for edge in edges
        if edge["source"] in selected_ids or edge["target"] in selected_ids or score_text(query_tokens, edge["summary"]) > 0
    ][: max(8, limit * 2)]

    scored_chunks = []
    for chunk in chunks:
        haystack = " ".join([chunk["id"], chunk["title"], chunk["summary"], " ".join(chunk["keywords"])])
        score = score_text(query_tokens, haystack)
        if score:
            scored_chunks.append((score, chunk))
    scored_chunks.sort(key=lambda item: (-item[0], item[1]["title"]))
    selected_chunks = [chunk for _, chunk in scored_chunks[:limit]]

    lines = [
        "# Tidy First Source Pack",
        "",
        f"Query: {query}",
        "",
        "## Nodes",
    ]
    for node in selected_nodes:
        lines.append(f"- {node['name']} ({node['id']}, {node['type']}): {node['summary']} [refs: {format_refs(node['source_refs'])}]")
    lines.extend(["", "## Relations"])
    for edge in selected_edges:
        lines.append(f"- {edge['source']} -[{edge['type']}]-> {edge['target']}: {edge['summary']} [refs: {format_refs(edge['source_refs'])}]")
    lines.extend(["", "## Topic Chunks"])
    for chunk in selected_chunks:
        lines.append(f"- {chunk['title']} ({chunk['id']}): {chunk['summary']} [refs: {format_refs(chunk['source_refs'])}]")
    lines.extend(["", "Use this pack as public-safe context. Do not quote full private OCR source text from it."])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--q", "--query", dest="query", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=6)
    args = parser.parse_args()
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_pack(args.query, args.limit), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
