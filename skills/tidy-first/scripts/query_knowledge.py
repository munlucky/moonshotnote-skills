#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1] / "references"
terms = [item.lower() for item in sys.argv[1:]]
for name in ["nodes.jsonl", "chunks.jsonl", "edges.jsonl"]:
    path = root / name
    if not path.is_file():
        continue
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        text = json.dumps(row, ensure_ascii=False).lower()
        if not terms or any(term in text for term in terms):
            print(f"{name}: {json.dumps(row, ensure_ascii=False)}")
