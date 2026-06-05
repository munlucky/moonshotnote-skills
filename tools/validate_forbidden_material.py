#!/usr/bin/env python3
"""Detect public rows that preserve code, table, exercise, or walkthrough shape."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


FILES = [
    "nodes.jsonl",
    "edges.jsonl",
    "chunks.jsonl",
    "coverage_matrix.jsonl",
    "query_qa.jsonl",
    "canonical_registry.jsonl",
    "promotion_records.jsonl",
]
CODE_RE = re.compile(
    r"(^|\n)\s*(class|def|import|from|return|for|while|if)\s+[A-Za-z_][A-Za-z0-9_]*"
    r"|(^|\n)\s*(public|private|protected)\s+(class|interface|static|final|void|[A-Z][A-Za-z0-9_]*)"
    r"|[{};]{3,}|=>|->"
)
TABLE_RE = re.compile(r"(\|[^\n]+\|[^\n]*\n\s*\|[-:| ]+\|)|(\t[^\n]+\t)")
EXERCISE_RE = re.compile(r"(?i)\b(exercise|quiz|문제\s*[0-9]+|연습\s*문제|정답|해답)\b")
WALKTHROUGH_RE = re.compile(r"(?i)\b(step\s*[1-9]|chapter\s+[1-9].+chapter\s+[1-9]|first.+second.+third)\b")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def public_text(row: dict[str, Any]) -> str:
    values: list[str] = []
    for key in ["name", "title", "summary", "question", "pass_criteria", "gap_reason", "limitations"]:
        value = row.get(key)
        if isinstance(value, str):
            values.append(value)
    for key in ["aliases", "keywords"]:
        value = row.get(key)
        if isinstance(value, list):
            values.extend(str(item) for item in value)
    return "\n".join(values)


def ident(row: dict[str, Any], filename: str) -> str:
    if filename == "edges.jsonl":
        return f"{row.get('source')}->{row.get('target')}"
    return str(row.get("id") or f"line-{row.get('_line_no')}")


def validate_skill(skill_dir: Path) -> int:
    checked = 0
    for filename in FILES:
        path = skill_dir / "references" / filename
        for row in load_jsonl(path):
            text = public_text(row)
            if CODE_RE.search(text):
                raise ValueError(f"{skill_dir.name}:{filename}:{ident(row, filename)} appears to preserve code shape")
            if TABLE_RE.search(text):
                raise ValueError(f"{skill_dir.name}:{filename}:{ident(row, filename)} appears to preserve table shape")
            if EXERCISE_RE.search(text):
                raise ValueError(f"{skill_dir.name}:{filename}:{ident(row, filename)} appears to preserve exercise material")
            if WALKTHROUGH_RE.search(text):
                raise ValueError(f"{skill_dir.name}:{filename}:{ident(row, filename)} appears to preserve walkthrough order")
            checked += 1
    return checked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--root", default="skills")
    args = parser.parse_args()
    try:
        for skill in [item.strip() for item in args.skills.split(",") if item.strip()]:
            checked = validate_skill(Path(args.root) / skill)
            print(f"{skill}: {checked} public rows free of forbidden material shapes")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
