#!/usr/bin/env python3
"""Build a lightweight codebase knowledge graph.

This script is intentionally conservative: it favors deterministic file,
symbol, import, test, and layer facts over speculative semantic summaries.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "0.2.0"
SCHEMA_VERSION = 2

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "bower_components",
    "dist",
    "build",
    "out",
    "target",
    "coverage",
    ".next",
    ".nuxt",
    ".turbo",
    ".cache",
    ".codebase-understanding",
    ".understand-anything",
}

BINARY_EXTS = {
    ".7z",
    ".avif",
    ".bmp",
    ".class",
    ".dll",
    ".doc",
    ".docx",
    ".eot",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jar",
    ".jpeg",
    ".jpg",
    ".lockb",
    ".mp3",
    ".mp4",
    ".otf",
    ".pdf",
    ".png",
    ".pyc",
    ".so",
    ".tar",
    ".ttf",
    ".wasm",
    ".webp",
    ".woff",
    ".woff2",
    ".zip",
}

LANGUAGE_BY_EXT = {
    ".astro": "astro",
    ".bat": "batch",
    ".c": "c",
    ".cc": "cpp",
    ".cmd": "batch",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".css": "css",
    ".go": "go",
    ".graphql": "graphql",
    ".h": "c",
    ".hpp": "cpp",
    ".html": "html",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".json": "json",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".md": "markdown",
    ".mjs": "javascript",
    ".php": "php",
    ".proto": "protobuf",
    ".ps1": "powershell",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".scss": "css",
    ".sh": "shell",
    ".sql": "sql",
    ".swift": "swift",
    ".tf": "terraform",
    ".toml": "toml",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".vue": "vue",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
}

LANGUAGE_BY_NAME = {
    "Dockerfile": "dockerfile",
    "Jenkinsfile": "jenkinsfile",
    "Makefile": "makefile",
    "Procfile": "procfile",
    "docker-compose.yml": "yaml",
    "docker-compose.yaml": "yaml",
}

PACKAGE_MANIFESTS = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "settings.gradle",
    "Gemfile",
    "composer.json",
    ".csproj",
    ".sln",
}

CODE_LANGUAGES = {
    "c",
    "cpp",
    "csharp",
    "go",
    "java",
    "javascript",
    "kotlin",
    "php",
    "python",
    "ruby",
    "rust",
    "swift",
    "typescript",
}

JS_IMPORT_RE = re.compile(
    r"""(?:
        import\s+(?:[^'"]+\s+from\s+)?['"](?P<imp1>[^'"]+)['"]|
        export\s+[^'"]+\s+from\s+['"](?P<imp2>[^'"]+)['"]|
        require\(\s*['"](?P<imp3>[^'"]+)['"]\s*\)
    )""",
    re.VERBOSE,
)
GENERIC_IMPORT_RE = re.compile(r"^\s*(?:import|from|using)\s+([A-Za-z0-9_./:@-]+)", re.MULTILINE)
GO_IMPORT_BLOCK_RE = re.compile(r"import\s*\((?P<body>.*?)\)", re.DOTALL)
GO_IMPORT_LINE_RE = re.compile(r"import\s+(?:[._A-Za-z0-9]+\s+)?\"(?P<path>[^\"]+)\"")

CLASS_RE = re.compile(
    r"^\s*(?:export\s+)?(?:abstract\s+)?(?:class|interface|struct|enum|record)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
FUNCTION_RE = re.compile(
    r"""\b(?:
        (?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(|
        (?:export\s+)?func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(|
        (?:export\s+)?fun\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(|
        (?:public|private|protected|static|final|suspend|async)\s+
        [A-Za-z0-9_<>,\[\]?]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(
    )""",
    re.VERBOSE,
)
ARROW_EXPORT_RE = re.compile(
    r"\b(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>"
)


def strip_json_comments(text: str) -> str:
    """Remove common JSONC comments without trying to be a full parser."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a codebase graph JSON file.")
    parser.add_argument("root", help="Repository root or subdirectory to scan.")
    parser.add_argument(
        "--no-root-discovery",
        action="store_true",
        help="Scan the provided directory exactly instead of climbing to the detected project root.",
    )
    parser.add_argument(
        "--project-root",
        help="Explicit project root for scanning, git metadata, and TypeScript resolver discovery.",
    )
    parser.add_argument(
        "--out",
        help="Output graph path. Defaults to <root>/.codebase-understanding/codebase-map.json.",
    )
    parser.add_argument("--max-files", type=int, default=2500, help="Maximum text files to scan.")
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=900_000,
        help="Skip symbol extraction for files larger than this many bytes.",
    )
    return parser.parse_args()


def run_git(root: Path, args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def resolve_git_root(path: Path) -> Path:
    root = path.resolve()
    git_root = run_git(root, ["rev-parse", "--show-toplevel"])
    if git_root:
        return Path(git_root).resolve()
    return root


PROJECT_ROOT_MARKERS = {
    "package.json",
    "pnpm-workspace.yaml",
    "yarn.lock",
    "bun.lockb",
    "tsconfig.json",
    "jsconfig.json",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "settings.gradle",
}


def resolve_project_root(path: Path) -> Path:
    """Find a useful project root even when the directory is not a git checkout."""
    root = path.resolve()
    git_root = run_git(root, ["rev-parse", "--show-toplevel"])
    if git_root:
        return Path(git_root).resolve()

    fallback = root
    for base in [root, *root.parents]:
        names = {child.name for child in base.iterdir()} if base.exists() and base.is_dir() else set()
        if names & PROJECT_ROOT_MARKERS:
            return base.resolve()
        if "README.md" in names and ("src" in names or "AGENTS.md" in names):
            fallback = base.resolve()
            break
        if base.parent == base:
            break
    return fallback


def resolve_extends_path(config_root: Path, value: str) -> Path | None:
    if not value or value.startswith("@"):
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = config_root / candidate
    if candidate.is_dir():
        candidate = candidate / "tsconfig.json"
    elif candidate.suffix == "":
        candidate = candidate.with_suffix(".json")
    return candidate.resolve()


def load_ts_config(config_path: Path, seen: set[Path] | None = None) -> dict[str, Any] | None:
    seen = seen or set()
    config_path = config_path.resolve()
    if config_path in seen:
        return None
    seen.add(config_path)
    try:
        raw = config_path.read_text(encoding="utf-8", errors="replace")
        config = json.loads(strip_json_comments(raw))
    except (OSError, json.JSONDecodeError):
        return None

    parent_data: dict[str, Any] = {}
    extends_value = config.get("extends")
    if isinstance(extends_value, str):
        extends_path = resolve_extends_path(config_path.parent, extends_value)
        if extends_path and extends_path.exists():
            parent_data = load_ts_config(extends_path, seen) or {}

    compiler_options = config.get("compilerOptions", {})
    if not isinstance(compiler_options, dict):
        compiler_options = {}

    config_root = config_path.parent.resolve()
    if "baseUrl" in compiler_options:
        base_url = (config_root / str(compiler_options["baseUrl"])).resolve()
    else:
        base_url = Path(str(parent_data.get("baseUrl", config_root))).resolve()

    raw_paths = compiler_options.get("paths", parent_data.get("rawPaths", {}))
    paths: list[dict[str, Any]] = []
    if isinstance(raw_paths, dict):
        for pattern, targets in raw_paths.items():
            if not isinstance(pattern, str) or not isinstance(targets, list):
                continue
            paths.append({"pattern": pattern, "targets": [str(t) for t in targets]})

    return {
        "configPath": str(config_path),
        "configRoot": str(config_root),
        "baseUrl": str(base_url),
        "rawPaths": raw_paths if isinstance(raw_paths, dict) else {},
        "paths": paths,
        "extends": str(extends_value) if isinstance(extends_value, str) else None,
    }


def discover_ts_resolvers(root: Path) -> list[dict[str, Any]]:
    """Load tsconfig/jsconfig resolvers, preferring the nearest config per source file."""
    configs: list[Path] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)
        base = Path(current)
        for name in ("tsconfig.json", "jsconfig.json"):
            if name in names:
                configs.append(base / name)

    resolvers: list[dict[str, Any]] = []
    for config_path in sorted(configs, key=lambda p: len(p.parts), reverse=True):
        resolver = load_ts_config(config_path)
        if resolver:
            resolvers.append(resolver)
    return resolvers


def list_files(root: Path) -> list[str]:
    git_files = run_git(root, ["ls-files", "-co", "--exclude-standard"])
    if git_files:
        return sorted({p.replace("\\", "/") for p in git_files.splitlines() if p.strip()})

    files: list[str] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)
        for name in sorted(names):
            full = Path(current) / name
            try:
                rel = full.relative_to(root).as_posix()
            except ValueError:
                continue
            files.append(rel)
    return files


def is_probably_text(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    if suffix in BINARY_EXTS:
        return False
    return True


def detect_language(path: str) -> str:
    name = Path(path).name
    if name.startswith("Dockerfile"):
        return "dockerfile"
    if name in LANGUAGE_BY_NAME:
        return LANGUAGE_BY_NAME[name]
    suffix = Path(path).suffix.lower()
    if name.startswith(".env"):
        return "env"
    if suffix:
        return LANGUAGE_BY_EXT.get(suffix, suffix.lstrip("."))
    return "unknown"


def detect_category(path: str, language: str) -> str:
    lower = path.lower()
    name = Path(path).name.lower()
    if is_test_path(path):
        return "test"
    if language in {"markdown", "rst"} or lower.startswith(("docs/", "doc/")):
        return "document"
    if "/references/" in f"/{lower}/":
        return "document"
    if name in {"dockerfile", "docker-compose.yml", "docker-compose.yaml"}:
        return "infrastructure"
    if lower.startswith((".github/", ".gitlab/", ".circleci/")):
        return "pipeline"
    if language in {"yaml", "json", "toml", "xml", "env"} or name in PACKAGE_MANIFESTS:
        return "config"
    if language in {"sql", "graphql", "protobuf"}:
        return "schema"
    if language in {
        "python",
        "typescript",
        "javascript",
        "java",
        "go",
        "rust",
        "ruby",
        "php",
        "csharp",
        "kotlin",
        "swift",
        "cpp",
        "c",
    }:
        return "code"
    return "other"


def is_test_path(path: str) -> bool:
    lower = path.lower()
    name = Path(path).name.lower()
    return (
        "/test/" in f"/{lower}/"
        or "/tests/" in f"/{lower}/"
        or "/__tests__/" in f"/{lower}/"
        or name.startswith("test_")
        or name.endswith("_test.py")
        or ".test." in name
        or ".spec." in name
        or name.endswith("test.java")
        or name.endswith("tests.cs")
    )


def detect_layer(path: str, category: str) -> str:
    lower = path.lower()
    parts = set(lower.replace("\\", "/").split("/"))
    if category == "test":
        return "tests"
    if category == "document":
        return "docs"
    if category in {"pipeline", "infrastructure"} or parts & {
        "deploy",
        "deployment",
        "docker",
        "infra",
        "k8s",
        "kubernetes",
        "terraform",
    }:
        return "infrastructure"
    if category == "config":
        return "infrastructure"
    if parts & {
        "api",
        "apis",
        "controller",
        "controllers",
        "route",
        "routes",
        "pages",
        "components",
        "views",
        "ui",
        "screens",
        "hooks",
        "ink",
    }:
        return "interface"
    if parts & {
        "service",
        "services",
        "usecase",
        "usecases",
        "application",
        "commands",
        "handlers",
        "entrypoints",
        "query",
        "tools",
        "tasks",
        "remote",
        "script",
        "scripts",
        "server",
    }:
        return "application"
    if parts & {"domain", "model", "models", "entity", "entities", "aggregate", "aggregates", "types", "schemas"}:
        return "domain"
    if parts & {"repository", "repositories", "dao", "db", "database", "migrations", "persistence", "schema"}:
        return "data"
    if parts & {"util", "utils", "common", "shared", "lib", "helpers"}:
        return "utility"
    return "unknown"


def read_text(path: Path, max_bytes: int) -> str | None:
    try:
        if path.stat().st_size > max_bytes:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def line_count(text: str | None) -> int:
    if text is None:
        return 0
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def complexity_for(lines: int, symbol_count: int) -> str:
    score = lines + symbol_count * 25
    if score >= 450:
        return "complex"
    if score >= 140:
        return "moderate"
    return "simple"


def confidence_for(text: str | None, symbols: list[dict[str, Any]], imports: list[str]) -> float:
    if text is None:
        return 0.35
    score = 0.52
    if symbols:
        score += 0.12
    if imports:
        score += 0.06
    if len(text) > 500:
        score += 0.05
    return min(score, 0.78)


def responsibility_for(path: str, category: str, layer: str, symbols: list[dict[str, Any]]) -> str:
    name = Path(path).name
    if category == "test":
        return f"Exercises or verifies behavior related to {name}."
    if category == "config":
        return f"Configures build, runtime, tool, or environment behavior for {name}."
    if category == "document":
        return f"Documents project behavior, decisions, or usage around {name}."
    if category == "schema":
        return f"Defines data, API, query, or persistence shape in {name}."
    if symbols:
        symbol_names = ", ".join(symbol["name"] for symbol in symbols[:6])
        return f"Groups {len(symbols)} detected symbol(s) in the {layer} layer: {symbol_names}."
    return f"Contributes {category} behavior in the {layer} layer."


def layer_reason_for(path: str, category: str, layer: str) -> str:
    parts = set(path.lower().replace("\\", "/").split("/"))
    if category in {"test", "document", "config", "pipeline", "infrastructure"}:
        return f"Placed in {layer} because the file category is {category}."
    matched = sorted(parts & {
        "api",
        "application",
        "commands",
        "components",
        "controller",
        "controllers",
        "data",
        "db",
        "domain",
        "handlers",
        "hooks",
        "infra",
        "lib",
        "models",
        "repository",
        "routes",
        "schema",
        "schemas",
        "service",
        "services",
        "tools",
        "ui",
        "utils",
    })
    if matched:
        return f"Placed in {layer} from path segment(s): {', '.join(matched[:5])}."
    return f"Placed in {layer} by fallback layer heuristic."


def risk_hints_for(path: str, category: str, complexity: str, lines: int, symbols: list[dict[str, Any]]) -> list[str]:
    hints: list[str] = []
    lower = path.lower()
    if complexity == "complex":
        hints.append("high line/symbol count; inspect local control flow before editing")
    elif complexity == "moderate":
        hints.append("moderate size; check contained symbols and imports before editing")
    if category == "config":
        hints.append("configuration changes can affect runtime, build, or tooling globally")
    if category == "test":
        hints.append("test file; update alongside production behavior")
    if any(part in lower for part in ("auth", "permission", "security", "token", "secret")):
        hints.append("security-sensitive naming; verify auth and permission behavior")
    if lines == 0 and category == "code":
        hints.append("source unreadable or empty in scan; verify file contents directly")
    if len(symbols) > 25:
        hints.append("many symbols in one file; changes may have broad local blast radius")
    return hints


def symbol_risk_hints_for(path: str, category: str) -> list[str]:
    hints: list[str] = []
    lower = path.lower()
    if any(part in lower for part in ("auth", "permission", "security", "token", "secret")):
        hints.append("security-sensitive containing file; verify auth and permission behavior")
    if category == "test":
        hints.append("test symbol; keep assertions aligned with production behavior")
    return hints


def language_notes_for(language: str, imports: list[str]) -> str:
    if language in {"typescript", "javascript"}:
        return "JavaScript/TypeScript module; import resolution is heuristic unless a local tsconfig/jsconfig mapping resolves it."
    if language == "python":
        return "Python module parsed with the standard ast parser when syntax is valid."
    if imports:
        return f"{language} file with {len(imports)} detected import/reference statement(s)."
    return f"{language} file detected by extension or filename."


def evidence_for(path: str, text: str | None, line_range: list[int] | None = None) -> list[dict[str, Any]]:
    if line_range:
        return [{"kind": "source", "filePath": path, "lineRange": line_range}]
    if text:
        end = min(line_count(text), 40)
        return [{"kind": "source", "filePath": path, "lineRange": [1, end]}]
    return [{"kind": "path", "filePath": path}]


def extract_python_symbols(path: str, text: str) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [], []

    symbols: list[dict[str, Any]] = []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(
                {
                    "type": "function",
                    "name": node.name,
                    "lineRange": [node.lineno, getattr(node, "end_lineno", node.lineno)],
                }
            )
        elif isinstance(node, ast.ClassDef):
            symbols.append(
                {
                    "type": "class",
                    "name": node.name,
                    "lineRange": [node.lineno, getattr(node, "end_lineno", node.lineno)],
                }
            )
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append("." * node.level + node.module)
    return symbols, imports


def extract_regex_symbols(text: str) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    line_starts = [0]
    for match in re.finditer("\n", text):
        line_starts.append(match.end())

    def line_no(pos: int) -> int:
        lo, hi = 0, len(line_starts)
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid
        return lo + 1

    for pattern, symbol_type in ((CLASS_RE, "class"), (FUNCTION_RE, "function"), (ARROW_EXPORT_RE, "function")):
        for match in pattern.finditer(text):
            name = match.group(1)
            if name is None:
                name = next(group for group in match.groups() if group)
            if name in {"if", "for", "while", "switch", "catch", "return"}:
                continue
            key = (symbol_type, name)
            if key in seen:
                continue
            seen.add(key)
            line = line_no(match.start())
            symbols.append({"type": symbol_type, "name": name, "lineRange": [line, line]})
    return symbols


def extract_imports(language: str, text: str) -> list[str]:
    imports: list[str] = []
    if language in {"javascript", "typescript", "vue", "astro"}:
        for match in JS_IMPORT_RE.finditer(text):
            value = match.group("imp1") or match.group("imp2") or match.group("imp3")
            if value:
                imports.append(value)
    elif language == "go":
        for match in GO_IMPORT_LINE_RE.finditer(text):
            imports.append(match.group("path"))
        for block in GO_IMPORT_BLOCK_RE.finditer(text):
            imports.extend(re.findall(r'"([^"]+)"', block.group("body")))
    else:
        imports.extend(match.group(1) for match in GENERIC_IMPORT_RE.finditer(text))
    return imports


def extract_symbols(path: str, language: str, text: str | None) -> tuple[list[dict[str, Any]], list[str]]:
    if text is None:
        return [], []
    if language == "python":
        return extract_python_symbols(path, text)
    if language not in CODE_LANGUAGES:
        return [], []
    symbols = extract_regex_symbols(text) if language != "markdown" else []
    imports = extract_imports(language, text)
    return symbols, imports


def resolve_internal_import(
    root: Path,
    source_path: str,
    import_value: str,
    known_files: set[str],
    ts_resolvers: list[dict[str, Any]],
) -> str | None:
    if not import_value:
        return None

    source_dir = Path(source_path).parent
    candidates: list[str] = []

    if import_value.startswith("."):
        base = (source_dir / import_value).as_posix()
        candidates.extend(expand_import_candidates(base))
    else:
        candidates.extend(resolve_ts_candidates(root, source_path, import_value, ts_resolvers))
        normalized = import_value.replace(".", "/").strip("/")
        candidates.extend(expand_import_candidates(normalized))

    for candidate in candidates:
        if candidate in known_files:
            return candidate
    return None


def select_ts_resolver(root: Path, source_path: str, resolvers: list[dict[str, Any]]) -> dict[str, Any] | None:
    source_dir = (root / source_path).resolve().parent
    for resolver in resolvers:
        config_root = Path(str(resolver["configRoot"])).resolve()
        try:
            source_dir.relative_to(config_root)
        except ValueError:
            continue
        return resolver
    return resolvers[0] if resolvers else None


def resolve_ts_candidates(
    root: Path,
    source_path: str,
    import_value: str,
    resolvers: list[dict[str, Any]],
) -> list[str]:
    if import_value.startswith(("@types/", "node:", "http:", "https:")):
        return []

    resolver = select_ts_resolver(root, source_path, resolvers)
    if not resolver:
        return []

    root = root.resolve()
    base_url = Path(str(resolver["baseUrl"])).resolve()
    candidates: list[str] = []

    for mapping in resolver.get("paths", []):
        pattern = str(mapping.get("pattern", ""))
        star_value: str | None = None
        if "*" in pattern:
            prefix, suffix = pattern.split("*", 1)
            if not import_value.startswith(prefix) or not import_value.endswith(suffix):
                continue
            star_value = import_value[len(prefix) : len(import_value) - len(suffix)]
        elif import_value != pattern:
            continue

        for target in mapping.get("targets", []):
            target_value = str(target)
            if star_value is not None:
                target_value = target_value.replace("*", star_value)
            candidates.extend(abs_to_scan_relative(root, base_url / target_value))

    candidates.extend(abs_to_scan_relative(root, base_url / import_value))
    return candidates


def abs_to_scan_relative(root: Path, path: Path) -> list[str]:
    try:
        rel_base = path.resolve().relative_to(root)
    except ValueError:
        return []
    return expand_import_candidates(rel_base.as_posix())


def expand_import_candidates(base: str) -> list[str]:
    base = base.replace("\\", "/").replace("//", "/").lstrip("./")
    suffixes = [
        "",
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".java",
        ".go",
        "/__init__.py",
        "/index.ts",
        "/index.tsx",
        "/index.js",
        "/index.jsx",
        ".d.ts",
        ".mts",
        ".cts",
        ".cjs",
        "/index.d.ts",
        "/index.mts",
        "/index.cts",
        "/index.mjs",
        "/index.cjs",
    ]
    return [f"{base}{suffix}" for suffix in suffixes]


def detect_framework_hints(root: Path, files: list[str]) -> list[str]:
    names = {Path(path).name.lower() for path in files}
    lower_paths = [path.lower() for path in files]
    hints: set[str] = set()
    if "package.json" in names:
        package_paths = [path for path in files if Path(path).name == "package.json"]
        for package_path in package_paths[:5]:
            text = read_text(root / package_path, 250_000)
            if not text:
                continue
            lowered = text.lower()
            for name in ("react", "next", "vue", "vite", "express", "nestjs", "astro"):
                if f'"{name}"' in lowered or f"@{name}/" in lowered:
                    hints.add(name)
    if "pyproject.toml" in names or "requirements.txt" in names:
        joined = "\n".join(lower_paths)
        for name in ("fastapi", "django", "flask", "pytest"):
            if name in joined:
                hints.add(name)
    if "pom.xml" in names or "build.gradle" in names:
        hints.add("jvm")
        if any("spring" in path for path in lower_paths):
            hints.add("spring")
    if "go.mod" in names:
        hints.add("go")
    if "cargo.toml" in names:
        hints.add("rust")
    return sorted(hints)


def build_graph(root: Path, files: list[str], max_files: int, max_bytes: int) -> dict[str, Any]:
    text_files = [path for path in files if is_probably_text(path)]
    limited_files = text_files[:max_files]
    known_files = set(limited_files)
    ts_resolvers = discover_ts_resolvers(root)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    layers: dict[str, list[str]] = defaultdict(list)
    languages = Counter()
    categories = Counter()
    skipped_large = 0

    file_meta: dict[str, dict[str, Any]] = {}
    imports_by_file: dict[str, list[str]] = {}

    for rel_path in limited_files:
        language = detect_language(rel_path)
        category = detect_category(rel_path, language)
        layer = detect_layer(rel_path, category)
        abs_path = root / rel_path
        text = read_text(abs_path, max_bytes)
        if text is None and abs_path.exists():
            skipped_large += 1
        lines = line_count(text)
        symbols, imports = extract_symbols(rel_path, language, text)
        node_type = "test" if category == "test" else file_node_type(category)
        complexity = complexity_for(lines, len(symbols))
        node_id = f"file:{rel_path}"

        languages[language] += 1
        categories[category] += 1
        layers[layer].append(node_id)
        file_meta[rel_path] = {
            "nodeId": node_id,
            "language": language,
            "category": category,
            "layer": layer,
            "symbols": symbols,
        }
        imports_by_file[rel_path] = imports

        nodes.append(
            {
                "id": node_id,
                "type": node_type,
                "name": Path(rel_path).name,
                "filePath": rel_path,
                "summary": f"{category} file in {layer} layer; {lines} lines; {len(symbols)} symbols",
                "responsibility": responsibility_for(rel_path, category, layer, symbols),
                "evidence": evidence_for(rel_path, text),
                "confidence": confidence_for(text, symbols, imports),
                "layerReason": layer_reason_for(rel_path, category, layer),
                "riskHints": risk_hints_for(rel_path, category, complexity, lines, symbols),
                "languageNotes": language_notes_for(language, imports),
                "tags": sorted({language, category, layer}),
                "complexity": complexity,
                "metrics": {"lines": lines, "symbols": len(symbols)},
            }
        )

        seen_symbol_ids: set[str] = set()
        for symbol in symbols:
            symbol_id = f"{symbol['type']}:{rel_path}:{symbol['name']}"
            if symbol_id in seen_symbol_ids:
                symbol_id = f"{symbol_id}:L{symbol['lineRange'][0]}"
            seen_symbol_ids.add(symbol_id)
            nodes.append(
                {
                    "id": symbol_id,
                    "type": symbol["type"],
                    "name": symbol["name"],
                    "filePath": rel_path,
                    "lineRange": symbol["lineRange"],
                    "summary": f"{symbol['type']} defined in {rel_path}",
                    "responsibility": f"Defines `{symbol['name']}` inside {rel_path}.",
                    "evidence": evidence_for(rel_path, text, symbol["lineRange"]),
                    "confidence": confidence_for(text, symbols, imports),
                    "layerReason": layer_reason_for(rel_path, category, layer),
                    "riskHints": symbol_risk_hints_for(rel_path, category),
                    "languageNotes": language_notes_for(language, imports),
                    "tags": sorted({language, layer, symbol["type"]}),
                    "complexity": "simple",
                }
            )
            edges.append(
                {
                    "source": node_id,
                    "target": symbol_id,
                    "type": "contains",
                    "direction": "forward",
                    "weight": 1.0,
                }
            )

    for source_path, imports in imports_by_file.items():
        source_id = file_meta[source_path]["nodeId"]
        for import_value in imports:
            target_path = resolve_internal_import(root, source_path, import_value, known_files, ts_resolvers)
            if not target_path or target_path == source_path:
                continue
            edges.append(
                {
                    "source": source_id,
                    "target": file_meta[target_path]["nodeId"],
                    "type": "imports",
                    "direction": "forward",
                    "weight": 0.8,
                    "description": f"imports {import_value}",
                }
            )

    add_test_edges(file_meta, edges)

    commit = run_git(root, ["rev-parse", "HEAD"]) or "unknown"
    graph_layers = make_layers(layers)
    graph = {
        "version": VERSION,
        "schemaVersion": SCHEMA_VERSION,
        "kind": "codebase",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "project": {
            "name": root.name,
            "root": str(root),
            "gitCommitHash": commit,
            "languages": [item for item, _ in languages.most_common()],
            "frameworkHints": detect_framework_hints(root, limited_files),
            "resolver": resolver_summary(root, ts_resolvers),
            "analysis": {
                "schemaVersion": SCHEMA_VERSION,
                "deterministicAnalyzer": VERSION,
                "semanticMode": "deterministic-seed",
                "platform": sys.platform,
                "pathStyle": "posix-normalized",
            },
        },
        "nodes": nodes,
        "edges": dedupe_edges(edges),
        "layers": graph_layers,
        "tour": make_tour(graph_layers),
        "summary": {
            "filesSeen": len(files),
            "textFilesScanned": len(limited_files),
            "filesSkippedByLimit": max(0, len(text_files) - len(limited_files)),
            "filesSkippedLarge": skipped_large,
            "nodes": len(nodes),
            "edges": len(edges),
            "languages": dict(languages.most_common()),
            "categories": dict(categories.most_common()),
        },
    }
    return graph


def resolver_summary(root: Path, resolvers: list[dict[str, Any]]) -> dict[str, Any]:
    if not resolvers:
        return {"typescript": None}
    configs: list[dict[str, Any]] = []
    total_paths = 0
    for resolver in resolvers:
        try:
            config_path = Path(str(resolver["configPath"])).resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            config_path = str(resolver["configPath"])
        total_paths += len(resolver.get("paths", []))
        configs.append(
            {
                "configPath": config_path,
                "baseUrl": str(resolver["baseUrl"]),
                "pathMappings": len(resolver.get("paths", [])),
                "extends": resolver.get("extends"),
            }
        )
    return {
        "typescript": {
            "configs": configs[:12],
            "configCount": len(resolvers),
            "pathMappings": total_paths,
        }
    }


def file_node_type(category: str) -> str:
    return {
        "config": "config",
        "document": "document",
        "infrastructure": "resource",
        "pipeline": "pipeline",
        "schema": "schema",
    }.get(category, "file")


def add_test_edges(file_meta: dict[str, dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    production = {path for path, meta in file_meta.items() if meta["category"] != "test"}
    for test_path, meta in file_meta.items():
        if meta["category"] != "test":
            continue
        candidates = possible_test_targets(test_path)
        for candidate in candidates:
            if candidate in production:
                edges.append(
                    {
                        "source": file_meta[candidate]["nodeId"],
                        "target": meta["nodeId"],
                        "type": "tested_by",
                        "direction": "forward",
                        "weight": 0.7,
                    }
                )
                break


def possible_test_targets(test_path: str) -> list[str]:
    path = test_path.replace("\\", "/")
    name = Path(path).name
    parent = Path(path).parent.as_posix()
    candidates: list[str] = []

    replacements = [
        (".test.", "."),
        (".spec.", "."),
        ("_test.", "."),
    ]
    prod_name = name
    for old, new in replacements:
        prod_name = prod_name.replace(old, new)
    if prod_name.startswith("test_"):
        prod_name = prod_name[5:]

    parent_variants = [
        parent.replace("/tests", "").replace("tests/", ""),
        parent.replace("/test", "").replace("test/", ""),
        parent,
    ]
    for base in parent_variants:
        if base in {".", ""}:
            candidates.append(prod_name)
        else:
            candidates.append(f"{base}/{prod_name}".lstrip("/"))
    return list(dict.fromkeys(candidates))


def dedupe_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for edge in edges:
        key = (edge["source"], edge["target"], edge["type"])
        if key in seen:
            continue
        seen.add(key)
        out.append(edge)
    return out


def make_layers(layer_nodes: dict[str, list[str]]) -> list[dict[str, Any]]:
    descriptions = {
        "interface": "User, API, route, page, and controller boundary files.",
        "application": "Use cases, services, handlers, and orchestration code.",
        "domain": "Domain models, entities, policies, and invariant-bearing code.",
        "data": "Persistence, repositories, migrations, and data schemas.",
        "infrastructure": "Configuration, build, deployment, CI, and runtime wiring.",
        "tests": "Automated tests, specs, and fixtures.",
        "docs": "Documentation and knowledge files.",
        "utility": "Shared helpers and common libraries.",
        "unknown": "Files without confident layer placement.",
    }
    ordered = []
    for layer_id in [
        "interface",
        "application",
        "domain",
        "data",
        "infrastructure",
        "tests",
        "docs",
        "utility",
        "unknown",
    ]:
        ids = sorted(set(layer_nodes.get(layer_id, [])))
        if not ids:
            continue
        ordered.append(
            {
                "id": layer_id,
                "name": layer_id.title(),
                "description": descriptions[layer_id],
                "nodeIds": ids,
            }
        )
    return ordered


def make_tour(layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tour = []
    for idx, layer in enumerate(layers, start=1):
        tour.append(
            {
                "order": idx,
                "title": f"Read {layer['name']}",
                "description": layer["description"],
                "nodeIds": layer["nodeIds"][:8],
            }
        )
    return tour


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args()
    requested_root = Path(args.root)
    if args.project_root:
        root = Path(args.project_root).resolve()
    elif args.no_root_discovery:
        root = requested_root.resolve()
    else:
        root = resolve_project_root(requested_root)
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root is not a directory: {root}")

    out = Path(args.out) if args.out else root / ".codebase-understanding" / "codebase-map.json"
    files = list_files(root)
    graph = build_graph(root, files, args.max_files, args.max_bytes)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {out} with {graph['summary']['textFilesScanned']} files, "
        f"{graph['summary']['nodes']} nodes, {len(graph['edges'])} edges."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
