#!/usr/bin/env python3
"""Audit public knowledge rows for direct-source leakage risk.

This gate is intentionally about expression copying, not concept use. It allows
public-safe concepts, relationships, and technical labels while blocking rows
that look like long quotations, copied code examples, table reconstructions, or
private-source path leaks. If ignored private chunks exist under a skill output
folder, it also performs a conservative shingle comparison against them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REFERENCE_SUFFIXES = {".jsonl", ".json", ".yaml", ".yml", ".md"}
PRIVATE_PATH_PATTERNS = [
    re.compile(r"(?i)[A-Z]:\\Users\\"),
    re.compile(r"(?i)Documents\\"),
]
TABLE_LIKE_PATTERNS = [
    re.compile(r"\|[^|\n]+\|[^|\n]+\|"),
    re.compile(r"(?m)^\s*\+[-+]{6,}\+"),
]


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.is_file():
        return rows
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        row["_source_file"] = path.name
        row["_line_no"] = line_no
        rows.append(row)
    return rows


def collect_strings(value, label: str) -> list[tuple[str, str]]:
    if isinstance(value, str) and value.strip():
        return [(label, value)]
    if isinstance(value, list):
        texts: list[tuple[str, str]] = []
        for idx, item in enumerate(value):
            texts.extend(collect_strings(item, f"{label}[{idx}]"))
        return texts
    if isinstance(value, dict):
        texts = []
        for key, item in value.items():
            if str(key).startswith("_"):
                continue
            texts.extend(collect_strings(item, f"{label}.{key}"))
        return texts
    return []


def public_texts(skill_dir: Path) -> list[tuple[str, str]]:
    refs = skill_dir / "references"
    texts: list[tuple[str, str]] = []
    for path in sorted(refs.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in REFERENCE_SUFFIXES:
            continue
        rel = path.relative_to(skill_dir)
        if path.suffix.lower() == ".jsonl":
            for row in load_jsonl(path):
                ident = row.get("id") or f"{row.get('source', '?')}->{row.get('target', '?')}"
                label = f"{skill_dir.name}/{rel}:{row['_line_no']}:{ident}"
                texts.extend(collect_strings(row, label))
            continue
        if path.suffix.lower() == ".json":
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                texts.append((f"{skill_dir.name}/{rel}", path.read_text(encoding="utf-8")))
            else:
                texts.extend(collect_strings(payload, f"{skill_dir.name}/{rel}"))
            continue
        texts.append((f"{skill_dir.name}/{rel}", path.read_text(encoding="utf-8")))
    return texts


def private_texts(skill_dir: Path) -> list[str]:
    roots = [skill_dir / "output" / "private-source", skill_dir / "outputs" / "private-source"]
    texts: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".txt", ".jsonl", ".md"}:
                continue
            try:
                texts.append(path.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                continue
    return texts


def word_tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9가-힣_]+", text.lower())


def shingles(tokens: list[str], width: int) -> set[tuple[str, ...]]:
    if len(tokens) < width:
        return set()
    return {tuple(tokens[i : i + width]) for i in range(len(tokens) - width + 1)}


def char_windows(text: str, width: int) -> set[str]:
    compact = re.sub(r"\s+", " ", text.strip())
    if len(compact) < width:
        return set()
    return {compact[i : i + width] for i in range(len(compact) - width + 1)}


def looks_like_code(text: str) -> bool:
    stripped = text.strip()
    if "```" in stripped:
        return True
    lines = stripped.splitlines() or [stripped]
    for line in lines:
        candidate = line.strip()
        if not candidate:
            continue
        if re.match(r"(?i)^select\s+.+\s+from\s+\w+", candidate):
            return True
        if re.match(r"^@[A-Za-z_][A-Za-z0-9_]*(?:\([^)]*\))?\s+class\s+\w+", candidate):
            return True
        if re.match(r"^import\s+[A-Za-z_][A-Za-z0-9_.]*(?:\s+as\s+\w+)?$", candidate):
            return True
        if re.match(r"^from\s+[A-Za-z_][A-Za-z0-9_.]*\s+import\s+[A-Za-z_*][A-Za-z0-9_*, ]*$", candidate):
            return True
        if re.match(r"^(class|def|function|public|private|protected|package)\s+\w+", candidate):
            return bool(re.search(r"[{}();=]|->", candidate))
        if re.match(r"^(for|while|if|try|catch)\s*\(.+\)\s*\{?", candidate):
            return True
    return False


def audit_skill(
    skill_dir: Path,
    max_verbatim_words: int,
    max_char_shingle: int,
    fail_on_source_code_match: bool,
    fail_on_table_or_exercise_match: bool,
) -> list[str]:
    findings: list[str] = []
    texts = public_texts(skill_dir)
    private = private_texts(skill_dir)
    private_word_shingles: set[tuple[str, ...]] = set()
    private_char_windows: set[str] = set()
    word_width = max(5, min(max_verbatim_words, 12))
    for private_text in private:
        private_word_shingles.update(shingles(word_tokens(private_text), word_width))
        private_char_windows.update(char_windows(private_text, max_char_shingle))

    for label, text in texts:
        encoded = text
        for pattern in PRIVATE_PATH_PATTERNS:
            if pattern.search(encoded):
                findings.append(f"{label}:private_path_leak")
        if fail_on_source_code_match and looks_like_code(encoded):
            findings.append(f"{label}:code_like_expression")
        if fail_on_table_or_exercise_match and any(pattern.search(encoded) for pattern in TABLE_LIKE_PATTERNS):
            findings.append(f"{label}:table_like_expression")
        if re.search(r"(?i)(exercise|연습문제|정답|해설)\s*\d+", encoded):
            findings.append(f"{label}:exercise_reconstruction_risk")
        if private_word_shingles and shingles(word_tokens(encoded), word_width) & private_word_shingles:
            findings.append(f"{label}:verbatim_word_shingle_match")
        if private_char_windows and char_windows(encoded, max_char_shingle) & private_char_windows:
            findings.append(f"{label}:verbatim_char_window_match")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True, help="Comma-separated skill names.")
    parser.add_argument("--root", default="skills")
    parser.add_argument("--max-verbatim-words", type=int, default=25)
    parser.add_argument("--max-char-shingle", type=int, default=80)
    parser.add_argument("--fail-on-source-code-match", action="store_true")
    parser.add_argument("--fail-on-table-or-exercise-match", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    findings: list[str] = []
    for skill in [item.strip() for item in args.skills.split(",") if item.strip()]:
        findings.extend(
            audit_skill(
                root / skill,
                args.max_verbatim_words,
                args.max_char_shingle,
                args.fail_on_source_code_match,
                args.fail_on_table_or_exercise_match,
            )
        )
    if findings:
        for finding in findings:
            print(finding)
        return 1
    print("Public verbatim audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
