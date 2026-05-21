#!/usr/bin/env python3
"""Query the public-safe Tidy First knowledge graph."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TOKEN_RE = re.compile(r"[A-Za-z0-9_./-]+|[가-힣]+")


def references_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "references"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def tokens(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def score_text(query_tokens: list[str], text: str) -> int:
    lower = text.lower()
    score = 0
    for token in query_tokens:
        if token in lower:
            score += 3 if len(token) > 2 else 1
    return score


def node_text(node: dict) -> str:
    return " ".join(
        [
            node.get("id", ""),
            node.get("type", ""),
            node.get("name", ""),
            node.get("summary", ""),
            " ".join(node.get("aliases", [])),
        ]
    )


def chunk_text(chunk: dict) -> str:
    return " ".join(
        [chunk.get("id", ""), chunk.get("title", ""), chunk.get("summary", ""), " ".join(chunk.get("keywords", []))]
    )


def query_graph(query: str, limit: int = 6) -> dict:
    refs = references_dir()
    nodes = load_jsonl(refs / "nodes.jsonl")
    edges = load_jsonl(refs / "edges.jsonl")
    chunks = load_jsonl(refs / "chunks.jsonl")
    query_tokens = tokens(query)

    node_hits = []
    for node in nodes:
        score = score_text(query_tokens, node_text(node))
        if score:
            node_hits.append({"score": score, **node})
    node_hits.sort(key=lambda item: (-item["score"], item["name"]))
    node_hits = node_hits[:limit]

    hit_ids = {node["id"] for node in node_hits}
    edge_hits = [
        edge
        for edge in edges
        if edge["source"] in hit_ids or edge["target"] in hit_ids or score_text(query_tokens, edge.get("summary", "")) > 0
    ][: max(limit * 2, 8)]

    chunk_hits = []
    for chunk in chunks:
        score = score_text(query_tokens, chunk_text(chunk))
        if score:
            chunk_hits.append({"score": score, **chunk})
    chunk_hits.sort(key=lambda item: (-item["score"], item["title"]))
    chunk_hits = chunk_hits[:limit]

    return {"query": query, "nodes": node_hits, "edges": edge_hits, "chunks": chunk_hits}


def print_text(result: dict) -> None:
    print(f"query: {result['query']}")
    print("\nNodes")
    for node in result["nodes"]:
        print(f"- {node['id']} ({node['type']}, score={node['score']}): {node['name']} - {node['summary']}")
    print("\nEdges")
    for edge in result["edges"]:
        print(f"- {edge['source']} -[{edge['type']}]-> {edge['target']}: {edge['summary']}")
    print("\nChunks")
    for chunk in result["chunks"]:
        print(f"- {chunk['id']} (score={chunk['score']}): {chunk['title']} - {chunk['summary']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--q", "--query", dest="query", required=True)
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = query_graph(args.query, args.limit)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
