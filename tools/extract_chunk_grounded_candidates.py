#!/usr/bin/env python3
"""Build private semantic candidate ledgers from OCR source chunks.

This tool reads ignored ``source_chunks.jsonl`` text and writes ignored,
public-safe candidate metadata under ``skills/<skill>/output``. It does not
copy source sentences into tracked references.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SOURCE_CHUNKS = {
    "tidy-first": "tidy-first-ocr/source_chunks.jsonl",
    "fastapi-clean-architecture": "fastapi-clean-architecture-reviewed-ocr/source_chunks.jsonl",
    "modern-java-in-action": "modern-java-in-action-reviewed-ocr/source_chunks.jsonl",
    "domain-driven-design-first-steps": "domain-driven-design-first-steps-ocr/source_chunks.jsonl",
    "spring-modern-api": "spring-modern-api-reviewed-ocr/source_chunks.jsonl",
    "python-architecture-patterns": "python-architecture-patterns-reviewed-ocr/source_chunks.jsonl",
}

SOURCE_IDS = {
    "tidy-first": "tidy-first-ocr",
    "fastapi-clean-architecture": "fastapi-clean-architecture-reviewed-ocr",
    "modern-java-in-action": "modern-java-in-action-reviewed-ocr",
    "domain-driven-design-first-steps": "domain-driven-design-first-steps-ocr",
    "spring-modern-api": "spring-modern-api-reviewed-ocr",
    "python-architecture-patterns": "python-architecture-patterns-reviewed-ocr",
}

REVIEW_STATUS = {
    "tidy-first": "unreviewed_summary_only",
    "domain-driven-design-first-steps": "needs_review_summary_only",
}

COMMON_SIGNALS = {
    "dependency direction": ["dependency", "depend", "import", "inversion", "port", "adapter", "의존", "역전"],
    "boundary design": ["boundary", "layer", "context", "module", "interface", "contract", "경계", "계층", "모듈", "계약"],
    "testability": ["test", "fixture", "mock", "unit", "integration", "테스트", "검증"],
    "configuration": ["config", "setting", "environment", "profile", "property", "설정", "환경"],
    "error handling": ["error", "exception", "failure", "validation", "status", "오류", "예외", "검증"],
    "transaction": ["transaction", "commit", "rollback", "session", "unit of work", "트랜잭션", "커밋", "롤백"],
    "api contract": ["api", "request", "response", "schema", "controller", "router", "요청", "응답", "스키마"],
    "persistence": ["database", "repository", "entity", "query", "migration", "jpa", "sql", "데이터베이스", "저장소"],
    "domain model": ["domain", "aggregate", "entity", "value", "invariant", "ubiquitous", "도메인", "애그리거트"],
    "change sequencing": ["change", "refactor", "tidy", "sequence", "reversible", "coupling", "변경", "정리", "결합", "되돌"],
}

SKILL_SIGNALS = {
    "tidy-first": {
        "guard clause": ["guard", "clause", "condition", "early return", "보호", "조건", "빠른 반환"],
        "dead code": ["dead code", "unused", "delete", "remove", "죽은 코드", "사용하지", "삭제"],
        "cohesion": ["cohesion", "together", "locality", "order", "응집", "가까이", "순서"],
        "coupling": ["coupling", "coupled", "dependency", "결합", "의존"],
        "reversibility": ["reversible", "option", "small", "batch", "되돌", "선택", "작게", "배치"],
    },
    "fastapi-clean-architecture": {
        "FastAPI dependency injection": ["fastapi", "depends", "dependency", "inject"],
        "Pydantic schema": ["pydantic", "schema", "model", "validation"],
        "SQLAlchemy repository": ["sqlalchemy", "repository", "session", "database"],
        "JWT authentication": ["jwt", "token", "auth", "password"],
        "Alembic migration": ["alembic", "migration", "revision"],
    },
    "modern-java-in-action": {
        "lambda expression": ["lambda", "functional interface", "predicate", "consumer"],
        "stream pipeline": ["stream", "filter", "map", "collect", "pipeline"],
        "Optional absence": ["optional", "null", "absence", "present"],
        "CompletableFuture": ["completablefuture", "future", "async", "completion"],
        "collector reduction": ["collector", "grouping", "partition", "reduction"],
    },
    "domain-driven-design-first-steps": {
        "bounded context": ["bounded context", "context", "boundary", "language"],
        "subdomain classification": ["subdomain", "core", "supporting", "generic"],
        "aggregate consistency": ["aggregate", "invariant", "consistency", "transaction"],
        "domain event": ["domain event", "event", "command", "policy"],
        "context mapping": ["context map", "upstream", "downstream", "anticorruption"],
    },
    "spring-modern-api": {
        "Spring controller": ["controller", "requestmapping", "restcontroller", "mvc"],
        "dependency injection": ["bean", "inject", "ioc", "component"],
        "JPA persistence": ["jpa", "entity", "repository", "transaction"],
        "OpenAPI contract": ["openapi", "schema", "contract", "api"],
        "HATEOAS link": ["hateoas", "link", "resource", "representation"],
    },
    "python-architecture-patterns": {
        "architecture boundary": ["architecture", "boundary", "layer", "module"],
        "twelve factor": ["twelve", "factor", "config", "environment"],
        "event driven": ["event", "message", "queue", "broker"],
        "testing strategy": ["test", "pytest", "fixture", "tdd"],
        "observability": ["logging", "metrics", "profiling", "debugging"],
    },
}


@dataclass(frozen=True)
class Chunk:
    id: str
    line_start: int
    line_end: int
    text: str


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def blocked_flags(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ["empty"]
    flags: list[str] = []
    code_like = sum(
        1
        for line in lines
        if re.search(r"(^\s*(class|def|public|private|import|from|return|if|for|while)\b|[{};=]|->|=>)", line)
    )
    table_like = sum(1 for line in lines if line.count("|") >= 2 or line.count("\t") >= 2)
    exercise_like = sum(1 for line in lines if re.search(r"(?i)(exercise|quiz|연습\s*문제|문제\s*[0-9]+|정답|해답)", line))
    toc_like = sum(1 for line in lines if re.search(r"\.{4,}\s*\d+$|^\d+(\.\d+){1,3}\s+", line))
    if code_like / len(lines) > 0.28:
        flags.append("code_heavy")
    if table_like / len(lines) > 0.18:
        flags.append("table_heavy")
    if exercise_like >= 3 or exercise_like / len(lines) > 0.03:
        flags.append("exercise_or_qa")
    if toc_like / len(lines) > 0.35:
        flags.append("toc_or_index")
    if len(text) < 240:
        flags.append("too_short")
    return flags


def find_signals(skill: str, text: str) -> list[str]:
    haystack = normalize(text)
    signals: list[str] = []
    for label, needles in {**COMMON_SIGNALS, **SKILL_SIGNALS.get(skill, {})}.items():
        if any(needle in haystack for needle in needles):
            signals.append(label)
    signals = sorted(dict.fromkeys(signals))
    return signals or ["source-local semantic context"]


def extraction_kind(signals: list[str], flags: list[str]) -> str:
    if flags and not signals:
        return "blocked_or_low_signal"
    if any("boundary" in signal or "direction" in signal for signal in signals):
        return "boundary_or_dependency"
    if any("test" in signal or "error" in signal for signal in signals):
        return "practice_or_warning"
    if len(signals) >= 3:
        return "concept_cluster"
    return "concept"


def candidate_id(skill: str, chunk: Chunk, signals: list[str], flags: list[str]) -> str:
    digest = hashlib.sha256(
        json.dumps(
            {
                "skill": skill,
                "chunk_id": chunk.id,
                "line_range": [chunk.line_start, chunk.line_end],
                "signals": signals,
                "flags": flags,
            },
            ensure_ascii=True,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"cand-{skill}-{chunk.id}-{digest}".replace("_", "-")


def build_candidates(skill: str, repo: Path) -> list[dict[str, Any]]:
    chunk_path = repo / "skills" / skill / "output" / "private-source" / SOURCE_CHUNKS[skill]
    chunks = [
        Chunk(
            id=str(row["id"]),
            line_start=int(row["line_start"]),
            line_end=int(row["line_end"]),
            text=str(row.get("text") or ""),
        )
        for row in load_jsonl(chunk_path)
    ]
    rows: list[dict[str, Any]] = []
    for chunk in chunks:
        flags = blocked_flags(chunk.text)
        signals = find_signals(skill, chunk.text)
        semantic_strength = signals != ["source-local semantic context"]
        if semantic_strength:
            flags = [
                {
                    "code_heavy": "code_material_dropped",
                    "table_heavy": "table_material_dropped",
                    "exercise_or_qa": "exercise_material_dropped",
                }.get(flag, flag)
                for flag in flags
            ]
        accepted = not {"code_heavy", "table_heavy", "exercise_or_qa", "toc_or_index"} & set(flags)
        cid = candidate_id(skill, chunk, signals, flags)
        rows.append(
            {
                "candidate_id": cid,
                "source_id": SOURCE_IDS[skill],
                "source_chunk_id": chunk.id,
                "line_range": [chunk.line_start, chunk.line_end],
                "text_sha256": hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
                "extraction_kind": extraction_kind(signals, flags),
                "semantic_signals": signals[:8],
                "blocked_material_flags": flags,
                "accepted_for_public_graph": accepted,
                "abstraction_loss": "high" if skill in REVIEW_STATUS else "medium",
                "review_status": REVIEW_STATUS.get(skill, "chunk_text_extracted"),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--run-id", default="latest")
    args = parser.parse_args()

    repo = Path(args.repo_root)
    for skill in [item.strip() for item in args.skills.split(",") if item.strip()]:
        if skill not in SOURCE_CHUNKS:
            raise SystemExit(f"unsupported source skill: {skill}")
        rows = build_candidates(skill, repo)
        out_dir = repo / "skills" / skill / "output" / "extraction-candidates" / args.run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "semantic_candidates.jsonl"
        with out_path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        accepted = sum(1 for row in rows if row["accepted_for_public_graph"])
        print(f"{skill}: candidates {accepted}/{len(rows)} accepted -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
