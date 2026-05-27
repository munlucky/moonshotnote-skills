#!/usr/bin/env python3
"""Serve the self-contained codebase graph dashboard."""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import sys
import urllib.parse
import webbrowser
from pathlib import Path


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, dashboard_dir: Path, graph_path: Path, overlay_path: Path | None, root: Path | None, **kwargs):
        self.dashboard_dir = dashboard_dir
        self.graph_path = graph_path
        self.overlay_path = overlay_path
        self.root = root
        super().__init__(*args, directory=str(dashboard_dir), **kwargs)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/codebase-map.json":
            self.send_json_file(self.graph_path)
            return
        if parsed.path == "/diff-overlay.json":
            if self.overlay_path and self.overlay_path.exists():
                self.send_json_file(self.overlay_path)
            else:
                self.send_json({"changedNodeIds": [], "affectedNodeIds": [], "changedFiles": []})
            return
        if parsed.path == "/source":
            query = urllib.parse.parse_qs(parsed.query)
            self.send_source(query.get("path", [""])[0], query.get("start", ["1"])[0], query.get("end", ["120"])[0])
            return
        if self.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def send_json_file(self, path: Path) -> None:
        try:
            data = path.read_bytes()
        except OSError:
            self.send_error(404, f"Missing file: {path}")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, value: dict) -> None:
        data = json.dumps(value).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_source(self, rel_path: str, start_raw: str, end_raw: str) -> None:
        if not self.root:
            self.send_json({"ok": False, "error": "source root unavailable", "text": ""})
            return
        rel_path = rel_path.replace("\\", "/").lstrip("/")
        try:
            start = max(1, int(start_raw))
            end = max(start, int(end_raw))
        except ValueError:
            start, end = 1, 120
        target = (self.root / rel_path).resolve()
        try:
            target.relative_to(self.root.resolve())
        except ValueError:
            self.send_json({"ok": False, "error": "path escapes root", "text": ""})
            return
        try:
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            self.send_json({"ok": False, "error": str(exc), "text": ""})
            return
        selected = lines[start - 1 : min(end, len(lines))]
        text = "\n".join(f"{idx}: {line}" for idx, line in enumerate(selected, start=start))
        self.send_json({"ok": True, "path": rel_path, "lineRange": [start, min(end, len(lines))], "text": text})


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the codebase-understanding dashboard.")
    parser.add_argument("graph", help="Path to codebase-map.json.")
    parser.add_argument("--diff-overlay", help="Optional diff-overlay.json path.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--root", help="Repository root for source excerpts. Defaults to graph.project.root.")
    parser.add_argument("--no-open", action="store_true", help="Do not open a browser.")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    dashboard_dir = script_dir.parent / "assets" / "dashboard"
    graph_path = Path(args.graph).resolve()
    overlay_path = Path(args.diff_overlay).resolve() if args.diff_overlay else None
    if not graph_path.exists():
        raise SystemExit(f"Graph file not found: {graph_path}")
    if not (dashboard_dir / "index.html").exists():
        raise SystemExit(f"Dashboard asset not found: {dashboard_dir / 'index.html'}")

    root = Path(args.root).resolve() if args.root else None
    if not root:
        try:
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            if graph.get("project", {}).get("root"):
                root = Path(str(graph["project"]["root"])).resolve()
        except (OSError, json.JSONDecodeError):
            root = None

    handler = functools.partial(
        DashboardHandler,
        dashboard_dir=dashboard_dir,
        graph_path=graph_path,
        overlay_path=overlay_path,
        root=root,
    )
    with ReusableTCPServer((args.host, args.port), handler) as server:
        url = f"http://{args.host}:{server.server_address[1]}/"
        print(f"Dashboard started at {url}")
        print(f"Graph: {graph_path}")
        if root:
            print(f"Source root: {root}")
        if overlay_path:
            print(f"Diff overlay: {overlay_path}")
        if not args.no_open:
            webbrowser.open(url)
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
