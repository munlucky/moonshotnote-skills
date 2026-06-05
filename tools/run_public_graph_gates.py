#!/usr/bin/env python3
"""Run public graph validation gates skill by skill."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SOURCE_SKILLS = {
    "fastapi-clean-architecture",
    "spring-modern-api",
    "python-architecture-patterns",
    "domain-driven-design-first-steps",
    "modern-java-in-action",
    "tidy-first",
    "daily-webnovel-writing-knowledge-skill",
    "teddynote-langchain-rag",
}

PYTHON = [sys.executable]

SPECIFIC_VALIDATORS = {
    "fastapi-clean-architecture": [*PYTHON, "skills/fastapi-clean-architecture/scripts/validate_graph.py", "skills/fastapi-clean-architecture/references"],
    "spring-modern-api": [*PYTHON, "skills/spring-modern-api/scripts/validate_graph.py", "skills/spring-modern-api/references"],
    "modern-java-in-action": [*PYTHON, "skills/modern-java-in-action/scripts/validate_graph.py", "skills/modern-java-in-action/references"],
    "tidy-first": [*PYTHON, "skills/tidy-first/scripts/validate_graph.py", "skills/tidy-first/references"],
    "backend-architecture": [*PYTHON, "skills/backend-architecture/scripts/validate_graph.py", "skills/backend-architecture/references"],
}


def run(cmd: list[str], cwd: Path) -> None:
    print("+ " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd, text=True)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--profile", choices=["public-ci", "local-full"], default="public-ci")
    parser.add_argument("--run-id", default="latest")
    args = parser.parse_args()

    repo = Path(args.repo_root)
    skills = [item.strip() for item in args.skills.split(",") if item.strip()]
    for skill in skills:
        refs = f"skills/{skill}/references"
        run([*PYTHON, "skills/text-knowledge-skill-builder/scripts/lint_knowledge_pack.py", refs], repo)
        run([*PYTHON, "skills/text-knowledge-skill-builder/scripts/audit_public_safety.py", f"skills/{skill}"], repo)
        if skill in SPECIFIC_VALIDATORS:
            run(SPECIFIC_VALIDATORS[skill], repo)
        if skill in SOURCE_SKILLS:
            run([*PYTHON, "tools/validate_coverage_matrix.py", "--skills", skill, "--min-coverage", "0.95"], repo)
        run([*PYTHON, "tools/validate_edge_evidence.py", "--skills", skill], repo)
        run([*PYTHON, "tools/validate_query_qa.py", "--skills", skill, "--top-n", str(args.top_n)], repo)
        run([*PYTHON, "tools/validate_transform_trace.py", "--skills", skill], repo)
        run([*PYTHON, "tools/validate_forbidden_material.py", "--skills", skill], repo)
        run([*PYTHON, "tools/validate_substitution_risk.py", "--skills", skill], repo)
        if args.profile == "local-full":
            run([*PYTHON, "tools/validate_no_manifest_only_generation.py", "--skills", skill, "--run-id", args.run_id], repo)
            if skill in SOURCE_SKILLS:
                run([*PYTHON, "tools/validate_chunk_grounding.py", "--skills", skill, "--run-id", args.run_id], repo)
        run(
            [
                *PYTHON,
                "tools/audit_public_verbatim.py",
                "--skills",
                skill,
                "--max-verbatim-words",
                "25",
                "--max-char-shingle",
                "80",
                "--fail-on-source-code-match",
                "--fail-on-table-or-exercise-match",
            ],
            repo,
        )
    if "backend-architecture" in skills:
        run([*PYTHON, "tools/validate_backend_meta_artifacts.py", "--repo-root", "."], repo)
        run([*PYTHON, "skills/backend-architecture/scripts/build_from_source_skills.py", "--check"], repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
