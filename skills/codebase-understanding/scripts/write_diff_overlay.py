#!/usr/bin/env python3
"""Write a dashboard-readable diff overlay from changed files."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from graph_utils import configure_stdout, diff_nodes, load_graph


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create diff-overlay.json from graph impact context.")
    parser.add_argument("graph", help="Path to codebase-map.json.")
    parser.add_argument("--out", required=True, help="Output diff-overlay.json path.")
    parser.add_argument("--base-branch", default="working-tree", help="Base branch or label.")
    parser.add_argument("--changed-file", action="append", default=[], help="Changed repo-relative file.")
    parser.add_argument("--repo", help="Repository root. Used with --from-git.")
    parser.add_argument("--from-git", action="store_true", help="Use git diff --name-only from --repo.")
    parser.add_argument("--json", action="store_true", help="Print overlay JSON after writing.")
    return parser.parse_args()


def git_changed_files(repo: str, base_branch: str) -> list[str]:
    cmd = ["git", "-C", repo, "diff", "--name-only"]
    if base_branch and base_branch != "working-tree":
        cmd = ["git", "-C", repo, "diff", f"{base_branch}...HEAD", "--name-only"]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    configure_stdout()
    args = parse_args()
    changed_files = list(args.changed_file)
    if args.from_git:
        if not args.repo:
            raise SystemExit("--repo is required with --from-git")
        changed_files.extend(git_changed_files(args.repo, args.base_branch))
    changed_files = list(dict.fromkeys(path.replace("\\", "/").lstrip("./") for path in changed_files))
    if not changed_files:
        raise SystemExit("No changed files provided.")

    graph = load_graph(Path(args.graph))
    ctx = diff_nodes(graph, changed_files)
    changed_node_ids = [node["id"] for node in ctx["directNodes"]]
    affected_node_ids = [node["id"] for node in ctx["affectedNodes"]]
    overlay = {
        "version": "0.2.0",
        "baseBranch": args.base_branch,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "changedFiles": changed_files,
        "changedNodeIds": changed_node_ids,
        "affectedNodeIds": affected_node_ids,
        "unmappedFiles": ctx["unmappedFiles"],
        "risk": risk_summary(ctx),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(overlay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(overlay, ensure_ascii=False, indent=2))
    else:
        print(
            f"Wrote {out} with {len(changed_node_ids)} changed nodes, "
            f"{len(affected_node_ids)} affected nodes, {len(ctx['unmappedFiles'])} unmapped files."
        )
    return 0


def risk_summary(ctx: dict) -> dict:
    score = 0
    reasons = []
    complex_nodes = [node for node in ctx.get("directNodes", []) if node.get("complexity") == "complex"]
    if complex_nodes:
        score += 3
        reasons.append(f"{len(complex_nodes)} complex changed component(s)")
    if len(ctx.get("affectedNodes", [])) > 20:
        score += 3
        reasons.append(f"wide blast radius: {len(ctx.get('affectedNodes', []))} affected nodes")
    elif len(ctx.get("affectedNodes", [])) > 5:
        score += 2
        reasons.append(f"moderate blast radius: {len(ctx.get('affectedNodes', []))} affected nodes")
    if len(ctx.get("layers", [])) > 2:
        score += 2
        reasons.append(f"cross-layer impact: {len(ctx.get('layers', []))} layers")
    if ctx.get("unmappedFiles"):
        score += 2
        reasons.append(f"{len(ctx.get('unmappedFiles', []))} unmapped changed file(s)")
    if not reasons:
        reasons.append("localized graph impact")
    return {"level": "high" if score >= 5 else "medium" if score >= 2 else "low", "score": score, "reasons": reasons}


if __name__ == "__main__":
    raise SystemExit(main())
