from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def run_command(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, text=True, capture_output=True, check=False)
    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def resolve_cli(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found

    scripts_dir = Path(sys.executable).resolve().parent
    for candidate in (scripts_dir / name, scripts_dir / f"{name}.exe"):
        if candidate.exists():
            return str(candidate)
    return None


def collect_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        output = []
        for item in value:
            output.extend(collect_text(item))
        return output
    if isinstance(value, dict):
        output = []
        for key in ("text", "html", "markdown", "block_content"):
            if isinstance(value.get(key), str):
                output.append(value[key])
        for item in value.values():
            if isinstance(item, (dict, list)):
                output.extend(collect_text(item))
        return output
    return []


def normalize_box(box: Any) -> tuple[float, float, float, float] | None:
    if not box:
        return None
    if isinstance(box, list) and len(box) == 4 and all(isinstance(value, (int, float)) for value in box):
        x1, y1, x2, y2 = box
        return float(x1), float(y1), float(x2), float(y2)
    if isinstance(box, list):
        points: list[tuple[float, float]] = []
        for point in box:
            if isinstance(point, list) and len(point) >= 2:
                try:
                    points.append((float(point[0]), float(point[1])))
                except (TypeError, ValueError):
                    continue
        if points:
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            return min(xs), min(ys), max(xs), max(ys)
    return None

