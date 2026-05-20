#!/usr/bin/env python3
import importlib.util
import json
import platform
import shutil
import sys
from importlib import metadata
from pathlib import Path


REQUIRED_IMPORTS = [
    "PIL",
    "cv2",
    "numpy",
    "pandas",
    "paddle",
    "paddleocr",
    "surya",
]


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def resolve_cli(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found

    scripts_dir = Path(sys.executable).resolve().parent
    candidates = [scripts_dir / name, scripts_dir / f"{name}.exe"]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def main() -> int:
    skill_root = Path(__file__).resolve().parents[1]
    venv_python = skill_root / ".venv" / "Scripts" / "python.exe"

    checks = {
        "python": sys.executable,
        "python_version": sys.version.split()[0],
        "python_architecture": platform.architecture()[0],
        "machine": platform.machine(),
        "skill_root": str(skill_root),
        "expected_venv_python": str(venv_python),
        "running_inside_skill_venv": Path(sys.executable).resolve() == venv_python.resolve()
        if venv_python.exists()
        else False,
        "imports": {name: module_available(name) for name in REQUIRED_IMPORTS},
        "packages": {
            "paddlepaddle": package_version("paddlepaddle"),
            "paddleocr": package_version("paddleocr"),
            "surya-ocr": package_version("surya-ocr"),
            "transformers": package_version("transformers"),
        },
        "cli": {
            "surya": resolve_cli("surya"),
            "surya_ocr": resolve_cli("surya_ocr"),
            "paddleocr": resolve_cli("paddleocr"),
        },
    }

    print(json.dumps(checks, ensure_ascii=False, indent=2))

    missing = [name for name, ok in checks["imports"].items() if not ok]
    if missing:
        print("Missing imports: " + ", ".join(missing), file=sys.stderr)
        print("Run scripts/setup.ps1 from the skill directory.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
