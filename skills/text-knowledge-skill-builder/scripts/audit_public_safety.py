#!/usr/bin/env python3
"""Scan a publishable skill folder for private paths, personal data, secrets, and raw-source leakage."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


EXCLUDE_DIRS = {".git", ".venv", "__pycache__", "output", "outputs", "private-source", "cache", "models"}
EXCLUDE_FILES = {"audit_public_safety.py"}
PATTERNS = {
    "absolute_local_path": re.compile(r"(?i)([A-Z]:\\Users\\|/Users/|/home/)"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "korean_phone": re.compile(r"\b(?:01[016789][- ]?\d{3,4}[- ]?\d{4}|\d{2,3}[- ]\d{3,4}[- ]\d{4})\b"),
    "korean_rrn": re.compile(r"\b\d{6}[- ]?[1-4]\d{6}\b"),
    "secret_assignment": re.compile(r"(?i)\b(api[_-]?key|secret|password|passwd|token|bearer|cookie)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=:-]{8,}"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "database_url": re.compile(r"(?i)\b(mysql|postgres|postgresql|mongodb|redis)://[^\s'\"]+"),
}


def iter_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and path.name not in EXCLUDE_FILES and not any(part in EXCLUDE_DIRS for part in path.parts):
            yield path


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def is_pattern_literal_line(text: str, offset: int) -> bool:
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    if end == -1:
        end = len(text)
    line = text[start:end]
    return "re.compile(" in line


def audit(root: Path) -> list[str]:
    findings: list[str] = []
    for path in iter_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                if is_pattern_literal_line(text, match.start()):
                    continue
                findings.append(f"{path.relative_to(root)}:{line_number(text, match.start())}:{label}:{match.group(0)[:120]}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir")
    args = parser.parse_args()
    findings = audit(Path(args.skill_dir))
    if findings:
        for finding in findings:
            print(finding)
        return 1
    print("Public safety audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
