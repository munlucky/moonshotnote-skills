#!/usr/bin/env python3
"""Product-style entrypoint for the codebase-understanding workflow."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_chat_prompt import emit_prompt
from explain_graph import emit_markdown as emit_explain_markdown
from graph_utils import configure_stdout, diff_nodes, evidence_lines, explain_context, load_graph, node_map, query_nodes, source_excerpt
from scan_codebase import build_graph, list_files, resolve_project_root
from semantic_graph import merge_annotations, write_annotations, write_packs
from write_diff_overlay import git_changed_files


COMMANDS = {"analyze", "dashboard", "chat", "diff", "explain", "onboard", "semantic", "study"}

FILE_NODE_TYPES = {"file", "config", "document", "schema", "resource", "pipeline", "test"}
PRESET_QUERIES = {
    "entry": ["entry", "entrypoint", "cli", "main", "repl", "bootstrap", "launcher"],
    "prompt-flow": ["prompt", "input", "handlepromptsubmit", "processuserinput", "processtextprompt", "queryengine"],
    "tools": ["tool", "tools", "bashtool", "powershelltool", "execute", "result"],
    "permissions": ["permission", "permissions", "approval", "sandbox", "allow", "deny", "auth"],
    "messages": ["message", "messages", "transcript", "render", "assistant", "user"],
    "state-session": ["state", "session", "storage", "history", "context", "memory"],
    "commands": ["command", "commands", "slash", "handler", "mcp", "plugin"],
    "config-tests": ["config", "settings", "test", "tests", "spec", "fixture"],
}
STUDY_CHAPTERS = [
    ("01-entry-flow.md", "Entry Flow", "entry"),
    ("02-prompt-flow.md", "Prompt Flow", "prompt-flow"),
    ("03-tools.md", "Tools", "tools"),
    ("04-permissions.md", "Permissions", "permissions"),
    ("05-messages.md", "Messages", "messages"),
    ("06-state-session.md", "State And Session", "state-session"),
    ("07-commands-config-tests.md", "Commands, Config, Tests", "commands"),
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0] not in COMMANDS and argv[0] not in {"-h", "--help"}):
        argv.insert(0, "analyze")

    parser = argparse.ArgumentParser(
        description=(
            "Analyze a repository, save a codebase graph, and expose dashboard/chat/"
            "diff/explain/onboard consumer flows."
        )
    )
    subparsers = parser.add_subparsers(dest="command")

    add_analyze_args(subparsers.add_parser("analyze", help="Scan, save graph, then open dashboard by default."))

    dashboard = subparsers.add_parser("dashboard", help="Serve an existing graph dashboard.")
    add_common_args(dashboard)
    dashboard.add_argument("--graph", help="Existing codebase-map.json. Defaults to <root>/.codebase-understanding/codebase-map.json.")
    dashboard.add_argument("--diff-overlay", help="Optional diff-overlay.json.")
    add_server_args(dashboard)

    chat = subparsers.add_parser("chat", help="Build an LLM-ready prompt from a graph query.")
    add_common_args(chat)
    chat.add_argument("query", help="Question to answer from graph context.")
    chat.add_argument("--graph", help="Existing codebase-map.json.")
    chat.add_argument("--refresh", action="store_true", help="Refresh graph before building context.")
    chat.add_argument("--limit", type=int, default=12)
    chat.add_argument("--json", action="store_true")

    diff = subparsers.add_parser("diff", help="Analyze changed files and write diff-overlay.json.")
    add_common_args(diff)
    diff.add_argument("--graph", help="Existing codebase-map.json.")
    diff.add_argument("--refresh", action="store_true", help="Refresh graph before diff analysis.")
    diff.add_argument("--changed-file", action="append", default=[], help="Changed repo-relative file.")
    diff.add_argument("--base-branch", default="working-tree")
    diff.add_argument("--json", action="store_true")

    explain = subparsers.add_parser("explain", help="Deep-dive into one file, function, class, or node.")
    add_common_args(explain)
    explain.add_argument("target", help="File path, node id, node name, or file:path:symbol.")
    explain.add_argument("--graph", help="Existing codebase-map.json.")
    explain.add_argument("--refresh", action="store_true", help="Refresh graph before explanation.")
    explain.add_argument("--source-lines", type=int, default=80)
    explain.add_argument("--json", action="store_true")

    onboard = subparsers.add_parser("onboard", help="Generate an onboarding reading guide from the graph.")
    add_common_args(onboard)
    onboard.add_argument("--graph", help="Existing codebase-map.json.")
    onboard.add_argument("--refresh", action="store_true", help="Refresh graph before onboarding.")
    onboard.add_argument("--limit-per-layer", type=int, default=8)
    onboard.add_argument("--json", action="store_true")

    study = subparsers.add_parser("study", help="Generate a ranked study pack from the graph.")
    add_common_args(study)
    study.add_argument("--graph", help="Existing codebase-map.json.")
    study.add_argument("--refresh", action="store_true", help="Refresh graph before generating the study pack.")
    study.add_argument("--limit", type=int, default=80, help="Maximum ranked files to include unless --all is passed.")
    study.add_argument("--all", action="store_true", help="Include every file node in the study index.")
    study.add_argument(
        "--preset",
        action="append",
        choices=sorted(PRESET_QUERIES),
        default=[],
        help="Focus the study pack on one preset. Repeat for multiple presets.",
    )
    study.add_argument(
        "--exclude",
        action="append",
        default=[],
        choices=["docs", "tests", "config", "generated"],
        help="Exclude a broad file group. Repeat for multiple groups.",
    )
    study.add_argument("--reports-dir", help="Output directory. Defaults to <root>/.codebase-understanding/reports/study.")
    study.add_argument("--source-lines", type=int, default=24, help="Source excerpt lines per study card. Use 0 to omit.")
    study.add_argument("--json", action="store_true")

    semantic = subparsers.add_parser("semantic", help="Regenerate semantic packs/annotations and merge them into the graph.")
    add_common_args(semantic)
    semantic.add_argument("--graph", help="Existing codebase-map.json.")
    semantic.add_argument("--refresh", action="store_true", help="Refresh deterministic graph first.")
    semantic.add_argument("--json", action="store_true")

    return parser.parse_args(argv)


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("root", nargs="?", default=".", help="Repository root or subdirectory.")
    parser.add_argument("--project-root", help="Explicit project root.")
    parser.add_argument("--no-root-discovery", action="store_true", help="Use the provided root exactly.")
    parser.add_argument("--out-dir", help="Directory for codebase graph artifacts.")
    parser.add_argument("--max-files", type=int, default=2500)
    parser.add_argument("--max-bytes", type=int, default=900_000)
    parser.add_argument("--no-semantic", action="store_true", help="Skip semantic pack/annotation merge.")
    parser.add_argument("--semantic-limit", type=int, default=240, help="Maximum file nodes for semantic annotation.")
    parser.add_argument("--semantic-excerpt-lines", type=int, default=80)


def add_server_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--no-open", action="store_true", help="Do not open a browser.")


def add_analyze_args(parser: argparse.ArgumentParser) -> None:
    add_common_args(parser)
    add_server_args(parser)
    parser.add_argument("--no-dashboard", action="store_true", help="Only write graph artifacts.")
    parser.add_argument("--write-empty-overlay", action="store_true", help="Write an empty diff overlay when no git diff exists.")


def project_root(args: argparse.Namespace) -> Path:
    if getattr(args, "project_root", None):
        return Path(args.project_root).resolve()
    requested = Path(getattr(args, "root", ".")).resolve()
    if getattr(args, "no_root_discovery", False):
        return requested
    return resolve_project_root(requested)


def artifact_paths(args: argparse.Namespace, root: Path) -> tuple[Path, Path]:
    out_dir = Path(args.out_dir).resolve() if getattr(args, "out_dir", None) else root / ".codebase-understanding"
    return out_dir / "codebase-map.json", out_dir / "diff-overlay.json"


def artifact_dir(args: argparse.Namespace, root: Path) -> Path:
    return Path(args.out_dir).resolve() if getattr(args, "out_dir", None) else root / ".codebase-understanding"


def scan(root: Path, graph_path: Path, max_files: int, max_bytes: int) -> dict[str, Any]:
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root is not a directory: {root}")
    files = list_files(root)
    graph = build_graph(root, files, max_files, max_bytes)
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {graph_path} with {graph['summary']['textFilesScanned']} files, "
        f"{graph['summary']['nodes']} nodes, {len(graph['edges'])} edges."
    )
    return graph


def enrich_semantics(args: argparse.Namespace, root: Path, graph_path: Path, graph: dict[str, Any]) -> dict[str, Any]:
    if getattr(args, "no_semantic", False):
        return graph
    out_dir = artifact_dir(args, root)
    packs_dir = out_dir / "semantic-packs"
    annotations_path = out_dir / "semantic-annotations.json"
    packs = write_packs(graph, root, packs_dir, args.semantic_limit, args.semantic_excerpt_lines)
    annotations = write_annotations(graph, root, annotations_path, args.semantic_limit, args.semantic_excerpt_lines)
    annotations["path"] = str(annotations_path)
    merged = merge_annotations(graph, annotations)
    graph_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    coverage = merged.get("project", {}).get("analysis", {}).get("semanticCoverage", {})
    print(
        f"Semantic pass: {coverage.get('annotatedNodes', 0)} annotated file nodes; "
        f"packs: {packs_dir} ({packs.get('items', 0)} items)."
    )
    return merged


def ensure_graph(args: argparse.Namespace, refresh: bool = False) -> tuple[Path, Path, Path, dict[str, Any]]:
    root = project_root(args)
    graph_path, overlay_path = artifact_paths(args, root)
    explicit_graph = getattr(args, "graph", None)
    if explicit_graph:
        graph_path = Path(explicit_graph).resolve()
    if refresh or not graph_path.exists():
        graph = scan(root, graph_path, args.max_files, args.max_bytes)
        graph = enrich_semantics(args, root, graph_path, graph)
    else:
        graph = load_graph(graph_path)
    return root, graph_path, overlay_path, graph


def write_overlay(graph: dict[str, Any], overlay_path: Path, changed_files: list[str], base_branch: str) -> dict[str, Any]:
    ctx = diff_nodes(graph, changed_files)
    risk = diff_risk(ctx)
    overlay = {
        "version": "0.2.0",
        "baseBranch": base_branch,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "changedFiles": changed_files,
        "changedNodeIds": [node["id"] for node in ctx["directNodes"]],
        "affectedNodeIds": [node["id"] for node in ctx["affectedNodes"]],
        "unmappedFiles": ctx["unmappedFiles"],
        "risk": risk,
    }
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    overlay_path.write_text(json.dumps(overlay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return overlay


def diff_risk(ctx: dict[str, Any]) -> dict[str, Any]:
    direct = ctx.get("directNodes", [])
    affected = ctx.get("affectedNodes", [])
    layers = ctx.get("layers", [])
    reasons: list[str] = []
    score = 0
    complex_nodes = [node for node in direct if node.get("complexity") == "complex"]
    if complex_nodes:
        score += 3
        reasons.append(f"{len(complex_nodes)} complex changed component(s)")
    if len(affected) > 20:
        score += 3
        reasons.append(f"wide blast radius: {len(affected)} affected nodes")
    elif len(affected) > 5:
        score += 2
        reasons.append(f"moderate blast radius: {len(affected)} affected nodes")
    if len(layers) > 2:
        score += 2
        reasons.append(f"cross-layer impact: {len(layers)} layers")
    if ctx.get("unmappedFiles"):
        score += 2
        reasons.append(f"{len(ctx['unmappedFiles'])} unmapped changed file(s)")
    level = "high" if score >= 5 else "medium" if score >= 2 else "low"
    if not reasons:
        reasons.append("localized graph impact")
    return {"level": level, "score": score, "reasons": reasons}


def serve_dashboard(graph_path: Path, overlay_path: Path | None, host: str, port: int, no_open: bool, root: Path | None = None) -> int:
    script = Path(__file__).resolve().parent / "serve_dashboard.py"
    cmd = [
        sys.executable,
        str(script),
        str(graph_path),
        "--host",
        host,
        "--port",
        str(port),
    ]
    if overlay_path and overlay_path.exists():
        cmd.extend(["--diff-overlay", str(overlay_path)])
    if root:
        cmd.extend(["--root", str(root)])
    if no_open:
        cmd.append("--no-open")
    return subprocess.run(cmd, check=False).returncode


def command_analyze(args: argparse.Namespace) -> int:
    root = project_root(args)
    graph_path, overlay_path = artifact_paths(args, root)
    graph = scan(root, graph_path, args.max_files, args.max_bytes)
    graph = enrich_semantics(args, root, graph_path, graph)

    changed_files: list[str] = []
    try:
        changed_files = git_changed_files(str(root), "working-tree")
    except (subprocess.CalledProcessError, FileNotFoundError):
        changed_files = []

    if changed_files or args.write_empty_overlay:
        overlay = write_overlay(graph, overlay_path, changed_files, "working-tree")
        print(
            f"Wrote {overlay_path} with {len(overlay['changedNodeIds'])} changed nodes, "
            f"{len(overlay['affectedNodeIds'])} affected nodes, {len(overlay['unmappedFiles'])} unmapped files."
        )
    elif overlay_path.exists():
        overlay_path.unlink()
        print(f"Removed stale diff overlay: {overlay_path}")

    if args.no_dashboard:
        print_next_actions(root, graph_path, graph, changed_files)
        return 0
    print_next_actions(root, graph_path, graph, changed_files)
    return serve_dashboard(graph_path, overlay_path if overlay_path.exists() else None, args.host, args.port, args.no_open, root)


def print_next_actions(root: Path, graph_path: Path, graph: dict[str, Any], changed_files: list[str]) -> None:
    analysis = graph.get("project", {}).get("analysis", {})
    coverage = analysis.get("semanticCoverage", {})
    hotspots = top_hotspots(graph, 5)
    print("")
    print("Suggested next actions:")
    print(f"- Graph: {graph_path}")
    print(f"- Semantic coverage: {coverage.get('annotatedNodes', 0)}/{coverage.get('candidateFileNodes', 0) or 'unknown'} file nodes")
    if hotspots:
        print(f"- Hotspots: {', '.join(hotspots)}")
    if changed_files:
        print("- Run: diff --changed-file <path> for focused review context")
    if hotspots:
        print(f"- Run: explain {hotspots[0]}")
    print("- Run: chat \"이 저장소의 핵심 실행 흐름을 설명해줘\"")


def top_hotspots(graph: dict[str, Any], limit: int) -> list[str]:
    candidates = []
    for node in graph.get("nodes", []):
        if node.get("type") not in {"file", "config", "schema", "test"}:
            continue
        metrics = node.get("metrics", {})
        lines = int(metrics.get("lines", 0) or 0)
        symbols = int(metrics.get("symbols", 0) or 0)
        risk = len(node.get("riskHints", []) or [])
        complexity = {"complex": 3, "moderate": 2, "simple": 1}.get(str(node.get("complexity")), 0)
        score = complexity * 1000 + risk * 100 + symbols * 10 + lines
        candidates.append((score, str(node.get("filePath") or node.get("name"))))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [path for _, path in candidates[:limit]]


def command_dashboard(args: argparse.Namespace) -> int:
    root, graph_path, overlay_path, _ = ensure_graph(args)
    overlay = Path(args.diff_overlay).resolve() if getattr(args, "diff_overlay", None) else overlay_path
    return serve_dashboard(graph_path, overlay if overlay.exists() else None, args.host, args.port, args.no_open, root)


def command_chat(args: argparse.Namespace) -> int:
    _, _, _, graph = ensure_graph(args, args.refresh)
    ctx = query_nodes(graph, args.query, args.limit)
    if args.json:
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
    else:
        print(emit_prompt(ctx, args.query))
    return 0


def command_diff(args: argparse.Namespace) -> int:
    root, _, overlay_path, graph = ensure_graph(args, args.refresh)
    changed_files = list(args.changed_file)
    if not changed_files:
        changed_files = git_changed_files(str(root), args.base_branch)
    changed_files = list(dict.fromkeys(path.replace("\\", "/").lstrip("./") for path in changed_files))
    if not changed_files:
        raise SystemExit("No changed files found. Pass --changed-file or modify files first.")
    overlay = write_overlay(graph, overlay_path, changed_files, args.base_branch)
    if args.json:
        print(json.dumps(overlay, ensure_ascii=False, indent=2))
    else:
        print(emit_diff_report(graph, overlay_path, changed_files, overlay))
    return 0


def emit_diff_report(graph: dict[str, Any], overlay_path: Path, changed_files: list[str], overlay: dict[str, Any]) -> str:
    ctx = diff_nodes(graph, changed_files)
    lines = [
        f"# Diff Impact Report: {graph.get('project', {}).get('name', 'codebase')}",
        "",
        f"- Overlay: `{overlay_path}`",
        f"- Risk: **{overlay.get('risk', {}).get('level', 'unknown')}**",
        f"- Changed nodes: {len(overlay.get('changedNodeIds', []))}",
        f"- Affected nodes: {len(overlay.get('affectedNodeIds', []))}",
        f"- Unmapped files: {len(overlay.get('unmappedFiles', []))}",
        "",
        "## Risk Reasons",
    ]
    for reason in overlay.get("risk", {}).get("reasons", []):
        lines.append(f"- {reason}")
    lines.extend(["", "## Changed Components"])
    for node in ctx.get("directNodes", [])[:30]:
        lines.append(f"- `{node.get('filePath') or node.get('id')}` ({node.get('type')}, {node.get('complexity')}): {node.get('summary')}")
        for hint in node.get("riskHints", [])[:3]:
            lines.append(f"  - Risk: {hint}")
    if not ctx.get("directNodes"):
        lines.append("- No changed files mapped to graph nodes.")
    lines.extend(["", "## Affected Components"])
    for node in ctx.get("affectedNodes", [])[:40]:
        lines.append(f"- `{node.get('filePath') or node.get('id')}` ({node.get('type')}): {node.get('summary')}")
    if not ctx.get("affectedNodes"):
        lines.append("- No one-hop affected components found.")
    lines.extend(["", "## Review Focus"])
    test_nodes = [node for node in ctx.get("affectedNodes", []) if node.get("type") == "test"]
    if test_nodes:
        lines.append("- Run or inspect related tests:")
        for node in test_nodes[:12]:
            lines.append(f"  - `{node.get('filePath')}`")
    else:
        lines.append("- No directly connected tests found; search manually for coverage around changed files.")
    if overlay.get("unmappedFiles"):
        lines.append("- Refresh or widen the graph for unmapped files:")
        for path in overlay["unmappedFiles"][:20]:
            lines.append(f"  - `{path}`")
    return "\n".join(lines)


def command_explain(args: argparse.Namespace) -> int:
    root, _, _, graph = ensure_graph(args, args.refresh)
    ctx = explain_context(graph, args.target)
    if args.json:
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
    else:
        print(emit_explain_markdown(ctx, str(root), args.source_lines))
    return 0


def onboarding_context(graph: dict[str, Any], limit_per_layer: int) -> dict[str, Any]:
    by_id = {node["id"]: node for node in graph.get("nodes", [])}
    layers = []
    for layer in graph.get("layers", []):
        node_ids = layer.get("nodeIds", [])
        files = [
            by_id[node_id]
            for node_id in node_ids
            if node_id in by_id and by_id[node_id].get("type") in {"file", "config", "document", "schema", "resource", "pipeline", "test"}
        ]
        files.sort(key=onboarding_sort_key)
        layers.append(
            {
                "id": layer.get("id"),
                "name": layer.get("name"),
                "description": layer.get("description"),
                "files": files[:limit_per_layer],
            }
        )
    return {"project": graph.get("project", {}), "layers": layers, "summary": graph.get("summary", {})}


def onboarding_sort_key(node: dict[str, Any]) -> tuple[int, int, int, str]:
    path = str(node.get("filePath", node.get("name", ""))).replace("\\", "/")
    hidden_or_generated = int(path.startswith(".") or "/.claude/" in path or "/.agents/" in path)
    doc_priority = 0 if Path(path).name.lower() in {"readme.md", "agents.md", "prd.md", "spec.md"} else 1
    complexity_rank = {"complex": 0, "moderate": 1, "simple": 2}.get(str(node.get("complexity", "")), 3)
    return (hidden_or_generated, doc_priority, complexity_rank, path)


def emit_onboarding(ctx: dict[str, Any]) -> str:
    project = ctx.get("project", {})
    summary = ctx.get("summary", {})
    selected_files: list[dict[str, Any]] = []
    for layer in ctx.get("layers", []):
        selected_files.extend(layer.get("files", []))
    selected_files.sort(key=reading_priority)
    lines = [
        f"# Onboarding Guide: {project.get('name', 'codebase')}",
        "",
        "## Snapshot",
        f"- Root: `{project.get('root', '')}`",
        f"- Languages: {', '.join(project.get('languages', [])) or 'unknown'}",
        f"- Files scanned: {summary.get('textFilesScanned', 0)}",
        f"- Nodes: {summary.get('nodes', 0)}",
        f"- Edges: {summary.get('edges', 0)}",
        "",
        "## 30-Minute Path",
    ]
    for node in selected_files[:5]:
        lines.append(f"- `{node.get('filePath')}`: {node.get('responsibility') or node.get('summary', '')}")
    lines.extend(["", "## 2-Hour Path"])
    for node in selected_files[:15]:
        lines.append(f"- `{node.get('filePath')}` ({node.get('complexity')}): {node.get('summary', '')}")
    lines.extend(["", "## 1-Day Path"])
    for layer in ctx.get("layers", []):
        files = layer.get("files", [])
        if not files:
            continue
        lines.extend(["", f"### {layer.get('name')}", layer.get("description", "")])
        for node in files:
            lines.append(f"- `{node.get('filePath')}`: {node.get('responsibility') or node.get('summary', '')}")
            for hint in node.get("riskHints", [])[:2]:
                lines.append(f"  - Watch: {hint}")
    lines.extend(
        [
            "",
            "## Follow-Up Commands",
            "- `chat \"이 저장소의 핵심 실행 흐름을 설명해줘\"`",
            "- `explain <file>` for the first confusing file in the path",
            "- `diff --changed-file <path>` before reviewing a change",
            "",
            "## Operating Rule",
            "Treat this as a map. Verify behavior against source files, tests, and runtime output before making changes.",
        ]
    )
    return "\n".join(lines)


def reading_priority(node: dict[str, Any]) -> tuple[int, int, str]:
    path = str(node.get("filePath", "")).replace("\\", "/")
    name = Path(path).name.lower()
    if name in {"readme.md", "agents.md"}:
        return (0, 0, path)
    if name in {"package.json", "pyproject.toml", "go.mod", "cargo.toml", "pom.xml"}:
        return (1, 0, path)
    if name == "skill.md":
        return (2, 0, path)
    if "/scripts/" in path and node.get("type") == "file":
        return (3, {"complex": 0, "moderate": 1, "simple": 2}.get(str(node.get("complexity")), 3), path)
    if node.get("type") == "document":
        return (4, {"complex": 0, "moderate": 1, "simple": 2}.get(str(node.get("complexity")), 3), path)
    if node.get("type") == "file":
        return (5, {"complex": 0, "moderate": 1, "simple": 2}.get(str(node.get("complexity")), 3), path)
    if node.get("type") in {"config", "schema", "resource", "pipeline"}:
        return (6, 0, path)
    return (7, 0, path)


def command_onboard(args: argparse.Namespace) -> int:
    _, _, _, graph = ensure_graph(args, args.refresh)
    ctx = onboarding_context(graph, args.limit_per_layer)
    if args.json:
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
    else:
        print(emit_onboarding(ctx))
    return 0


def command_study(args: argparse.Namespace) -> int:
    root, _, _, graph = ensure_graph(args, args.refresh)
    reports_dir = Path(args.reports_dir).resolve() if args.reports_dir else root / ".codebase-understanding" / "reports" / "study"
    ctx = build_study_context(root, graph, args)
    written = write_study_reports(reports_dir, root, graph, ctx, args.source_lines)
    payload = {
        "reportsDir": str(reports_dir),
        "selectedFiles": len(ctx["selectedNodes"]),
        "totalFileNodes": ctx["totalFileNodes"],
        "presets": args.preset,
        "excluded": args.exclude,
        "files": [str(path) for path in written],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Study pack written: {reports_dir}")
        print(f"Selected files: {payload['selectedFiles']}/{payload['totalFileNodes']}")
        for path in written:
            print(f"- {path}")
    return 0


def build_study_context(root: Path, graph: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    by_id = node_map(graph)
    degrees = graph_degrees(graph)
    candidates = [
        node
        for node in graph.get("nodes", [])
        if isinstance(node, dict)
        and node.get("type") in FILE_NODE_TYPES
        and node.get("filePath")
        and not study_excluded(node, set(args.exclude))
    ]
    if args.preset:
        presets = set(args.preset)
        candidates = [node for node in candidates if any(node_matches_preset(node, preset) for preset in presets)]
    scored = []
    for node in candidates:
        scored.append((study_score(node, degrees), node))
    scored.sort(key=lambda item: (-item[0], str(item[1].get("filePath"))))
    selected = scored if args.all else scored[: max(0, args.limit)]
    selected_nodes = [with_study_metadata(graph, by_id, degrees, node, score) for score, node in selected]
    return {
        "root": str(root),
        "project": graph.get("project", {}),
        "summary": graph.get("summary", {}),
        "selectedNodes": selected_nodes,
        "totalFileNodes": len([node for node in graph.get("nodes", []) if isinstance(node, dict) and node.get("type") in FILE_NODE_TYPES and node.get("filePath")]),
        "candidateNodes": len(candidates),
        "layers": graph.get("layers", []),
    }


def graph_degrees(graph: dict[str, Any]) -> dict[str, dict[str, int]]:
    degrees: dict[str, dict[str, int]] = {}
    for edge in graph.get("edges", []):
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        degrees.setdefault(source, {"incoming": 0, "outgoing": 0})["outgoing"] += 1
        degrees.setdefault(target, {"incoming": 0, "outgoing": 0})["incoming"] += 1
    return degrees


def study_excluded(node: dict[str, Any], excludes: set[str]) -> bool:
    path = str(node.get("filePath", "")).replace("\\", "/").lower()
    node_type = str(node.get("type", ""))
    tags = {str(tag).lower() for tag in node.get("tags", [])}
    if "docs" in excludes and (node_type == "document" or "docs" in tags):
        return True
    if "tests" in excludes and (node_type == "test" or "tests" in tags or "test" in tags):
        return True
    if "config" in excludes and (node_type in {"config", "pipeline", "resource"} or "config" in tags):
        return True
    if "generated" in excludes and ("/generated/" in path or path.endswith(".d.ts")):
        return True
    return False


def node_text(node: dict[str, Any]) -> str:
    pieces = [
        node.get("id", ""),
        node.get("name", ""),
        node.get("filePath", ""),
        node.get("summary", ""),
        node.get("responsibility", ""),
        " ".join(str(tag) for tag in node.get("tags", [])),
        " ".join(str(hint) for hint in node.get("riskHints", [])),
    ]
    return " ".join(str(piece).lower() for piece in pieces)


def node_matches_preset(node: dict[str, Any], preset: str) -> bool:
    text = node_text(node)
    return any(keyword in text for keyword in PRESET_QUERIES.get(preset, []))


def study_score(node: dict[str, Any], degrees: dict[str, dict[str, int]]) -> int:
    path = str(node.get("filePath", "")).replace("\\", "/").lower()
    name = Path(path).name
    metrics = node.get("metrics", {}) if isinstance(node.get("metrics"), dict) else {}
    lines = int(metrics.get("lines", 0) or 0)
    symbols = int(metrics.get("symbols", 0) or 0)
    complexity = {"complex": 500, "moderate": 220, "simple": 60}.get(str(node.get("complexity")), 0)
    degree = degrees.get(str(node.get("id")), {"incoming": 0, "outgoing": 0})
    score = complexity + min(lines, 800) // 4 + symbols * 14 + degree["incoming"] * 18 + degree["outgoing"] * 12
    score += len(node.get("riskHints", []) or []) * 80
    if name in {"readme.md", "agents.md", "package.json", "pyproject.toml", "go.mod", "cargo.toml"}:
        score += 420
    if name in {"cli.tsx", "cli.ts", "main.ts", "main.tsx", "index.ts", "index.tsx", "app.tsx", "server.ts"}:
        score += 520
    for preset, keywords in PRESET_QUERIES.items():
        if any(keyword in path for keyword in keywords):
            score += 160
    if "/types/generated/" in path or "/generated/" in path:
        score -= 260
    return score


def with_study_metadata(
    graph: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    degrees: dict[str, dict[str, int]],
    node: dict[str, Any],
    score: int,
) -> dict[str, Any]:
    node_id = str(node.get("id"))
    children = []
    incoming_files = []
    outgoing_files = []
    for edge in graph.get("edges", []):
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        if edge.get("type") == "contains" and source == node_id and target in by_id:
            children.append(by_id[target])
        elif source == node_id and target in by_id and by_id[target].get("filePath"):
            outgoing_files.append(by_id[target])
        elif target == node_id and source in by_id and by_id[source].get("filePath"):
            incoming_files.append(by_id[source])
    enriched = dict(node)
    enriched["_study"] = {
        "score": score,
        "degree": degrees.get(node_id, {"incoming": 0, "outgoing": 0}),
        "symbols": children[:12],
        "incomingFiles": incoming_files[:8],
        "outgoingFiles": outgoing_files[:8],
        "presets": [preset for preset in PRESET_QUERIES if node_matches_preset(node, preset)],
    }
    return enriched


def write_study_reports(
    reports_dir: Path,
    root: Path,
    graph: dict[str, Any],
    ctx: dict[str, Any],
    source_lines: int,
) -> list[Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    selected = ctx["selectedNodes"]
    written: list[Path] = []

    overview = reports_dir / "00-overview.md"
    overview.write_text(emit_study_overview(graph, ctx), encoding="utf-8")
    written.append(overview)

    for filename, title, preset in STUDY_CHAPTERS:
        chapter_nodes = [node for node in selected if preset in node.get("_study", {}).get("presets", [])]
        if preset == "commands":
            chapter_nodes = [
                node
                for node in selected
                if any(item in node.get("_study", {}).get("presets", []) for item in ("commands", "config-tests"))
            ]
        if not chapter_nodes:
            continue
        path = reports_dir / filename
        path.write_text(emit_study_chapter(title, chapter_nodes, root, source_lines), encoding="utf-8")
        written.append(path)

    hotspots = reports_dir / "08-hotspots.md"
    hotspots.write_text(emit_study_chapter("Hotspots", selected[:40], root, source_lines), encoding="utf-8")
    written.append(hotspots)

    index = reports_dir / "99-file-index.md"
    index.write_text(emit_study_index(ctx), encoding="utf-8")
    written.append(index)
    return written


def emit_study_overview(graph: dict[str, Any], ctx: dict[str, Any]) -> str:
    project = graph.get("project", {})
    summary = graph.get("summary", {})
    selected = ctx["selectedNodes"]
    lines = [
        f"# Study Pack: {project.get('name', 'codebase')}",
        "",
        "## Snapshot",
        f"- Root: `{project.get('root', '')}`",
        f"- Languages: {', '.join(project.get('languages', [])) or 'unknown'}",
        f"- Files scanned: {summary.get('textFilesScanned', 0)}",
        f"- Nodes: {summary.get('nodes', 0)}",
        f"- Edges: {summary.get('edges', 0)}",
        f"- Semantic mode: {project.get('analysis', {}).get('semanticMode', 'unknown')}",
        f"- Selected study files: {len(selected)}/{ctx.get('totalFileNodes', 0)}",
        "",
        "## How To Study",
        "1. Read `01-entry-flow.md` first if it exists.",
        "2. Move through prompt, tools, permissions, messages, and state chapters.",
        "3. For a confusing card, run `understand_codebase.py explain <repo> <file>`.",
        "4. Use the dashboard to verify incoming/outgoing relationships visually.",
        "",
        "## Top Files",
    ]
    for node in selected[:30]:
        lines.append(f"- `{node.get('filePath')}` score {node['_study']['score']}: {node.get('summary', '')}")
    return "\n".join(lines) + "\n"


def emit_study_chapter(title: str, nodes: list[dict[str, Any]], root: Path, source_lines: int) -> str:
    lines = [f"# {title}", ""]
    for node in nodes:
        lines.extend(emit_study_card(node, root, source_lines))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def emit_study_card(node: dict[str, Any], root: Path, source_lines: int) -> list[str]:
    study = node.get("_study", {})
    lines = [
        f"## `{node.get('filePath')}`",
        "",
        f"- Score: {study.get('score', 0)}",
        f"- Type: {node.get('type')} / Complexity: {node.get('complexity')}",
        f"- Presets: {', '.join(study.get('presets', [])) or 'general'}",
        f"- Degree: in {study.get('degree', {}).get('incoming', 0)}, out {study.get('degree', {}).get('outgoing', 0)}",
        f"- Summary: {node.get('summary', '')}",
        f"- Responsibility: {node.get('responsibility', '')}",
    ]
    evidence = evidence_lines(node)
    if evidence:
        lines.append(f"- Evidence: {', '.join(evidence)}")
    if node.get("riskHints"):
        lines.append("- Risk hints:")
        for hint in node.get("riskHints", [])[:5]:
            lines.append(f"  - {hint}")
    symbols = study.get("symbols", [])
    if symbols:
        lines.append("- Key symbols:")
        for symbol in symbols[:10]:
            suffix = f" lines {symbol.get('lineRange')}" if symbol.get("lineRange") else ""
            lines.append(f"  - `{symbol.get('name')}` ({symbol.get('type')}){suffix}")
    connected = list(dict.fromkeys(
        str(item.get("filePath"))
        for item in [*study.get("outgoingFiles", []), *study.get("incomingFiles", [])]
        if item.get("filePath")
    ))
    if connected:
        lines.append("- Connected files:")
        for path in connected[:10]:
            lines.append(f"  - `{path}`")
    if source_lines > 0:
        excerpt = source_excerpt(root, node, source_lines)
        if excerpt:
            lines.extend(["", "```text", excerpt, "```"])
    return lines


def emit_study_index(ctx: dict[str, Any]) -> str:
    lines = [
        "# File Index",
        "",
        "Ranked file list generated from graph score, complexity, symbols, relationships, and semantic risk hints.",
        "",
        "| Score | File | Complexity | Presets |",
        "|---:|---|---|---|",
    ]
    for node in ctx["selectedNodes"]:
        presets = ", ".join(node.get("_study", {}).get("presets", [])) or "general"
        lines.append(
            f"| {node.get('_study', {}).get('score', 0)} | `{node.get('filePath')}` | {node.get('complexity')} | {presets} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    configure_stdout()
    args = parse_args()
    command = args.command or "analyze"
    if command == "analyze":
        return command_analyze(args)
    if command == "dashboard":
        return command_dashboard(args)
    if command == "chat":
        return command_chat(args)
    if command == "diff":
        return command_diff(args)
    if command == "explain":
        return command_explain(args)
    if command == "onboard":
        return command_onboard(args)
    if command == "study":
        return command_study(args)
    if command == "semantic":
        return command_semantic(args)
    raise SystemExit(f"Unknown command: {command}")


def command_semantic(args: argparse.Namespace) -> int:
    root, graph_path, _, graph = ensure_graph(args, args.refresh)
    graph = enrich_semantics(args, root, graph_path, graph)
    coverage = graph.get("project", {}).get("analysis", {}).get("semanticCoverage", {})
    if args.json:
        print(json.dumps(coverage, ensure_ascii=False, indent=2))
    else:
        print(
            f"Semantic graph updated: {coverage.get('annotatedNodes', 0)} annotated nodes, "
            f"{coverage.get('candidateFileNodes', 0)} candidate file nodes."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
