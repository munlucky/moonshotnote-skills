#!/usr/bin/env python3
import importlib.util
import json
import os
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

OPTIONAL_IMPORTS = [
    "transformers",
]


def default_runtime_root() -> Path:
    configured = os.environ.get("MOONSHOTNOTE_OCR_RUNTIME")
    if configured:
        return Path(configured).expanduser()
    relay_home = Path(os.environ.get("MOONSHOT_RELAY_HOME", Path.home() / ".moonshot-relay")).expanduser()
    return relay_home / "runtimes" / "moonshotnote-ocr-py312"


def runtime_python(runtime_root: Path) -> Path:
    return (
        runtime_root / "Scripts" / "python.exe"
        if os.name == "nt"
        else runtime_root / "bin" / "python"
    )


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


def pp_structure_capability() -> dict[str, object]:
    try:
        import paddleocr
    except Exception as exc:
        return {"available": False, "reason": f"paddleocr import failed: {exc}"}

    if not hasattr(paddleocr, "PPStructureV3"):
        return {"available": False, "reason": "paddleocr.PPStructureV3 is not available"}

    return {"available": True, "reason": None}


def main() -> int:
    skill_root = Path(__file__).resolve().parents[1]
    runtime_root = default_runtime_root()
    expected_runtime_python = runtime_python(runtime_root)
    legacy_skill_venv_python = (
        skill_root / ".venv" / "Scripts" / "python.exe"
        if os.name == "nt"
        else skill_root / ".venv" / "bin" / "python"
    )
    current_python = Path(sys.executable).resolve()

    checks = {
        "python": sys.executable,
        "python_version": sys.version.split()[0],
        "python_architecture": platform.architecture()[0],
        "machine": platform.machine(),
        "skill_root": str(skill_root),
        "runtime_root": str(runtime_root),
        "expected_runtime_python": str(expected_runtime_python),
        "running_inside_shared_runtime": current_python == expected_runtime_python.resolve()
        if expected_runtime_python.exists()
        else False,
        "legacy_skill_venv_python": str(legacy_skill_venv_python),
        "running_inside_legacy_skill_venv": current_python == legacy_skill_venv_python.resolve()
        if legacy_skill_venv_python.exists()
        else False,
        "required_imports": {name: module_available(name) for name in REQUIRED_IMPORTS},
        "optional_imports": {name: module_available(name) for name in OPTIONAL_IMPORTS},
        "packages": {
            "paddlepaddle": package_version("paddlepaddle"),
            "paddleocr": package_version("paddleocr"),
            "surya-ocr": package_version("surya-ocr"),
            "transformers": package_version("transformers"),
        },
        "optional_capabilities": {
            "pp_structure": pp_structure_capability(),
        },
        "cli": {
            "surya": resolve_cli("surya"),
            "surya_ocr": resolve_cli("surya_ocr"),
            "paddleocr": resolve_cli("paddleocr"),
        },
    }

    print(json.dumps(checks, ensure_ascii=False, indent=2))

    missing = [name for name, ok in checks["required_imports"].items() if not ok]
    if missing:
        print("Missing imports: " + ", ".join(missing), file=sys.stderr)
        print("Run scripts/setup.ps1 on Windows or scripts/setup.sh on macOS/Linux.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
