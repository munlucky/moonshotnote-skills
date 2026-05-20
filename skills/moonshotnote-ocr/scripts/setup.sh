#!/usr/bin/env bash
set -euo pipefail

PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
SKIP_INSTALL="${SKIP_INSTALL:-0}"
DISABLE_UV_FALLBACK="${DISABLE_UV_FALLBACK:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="$SKILL_ROOT/.venv"

run_checked() {
  "$@"
}

python_info_json() {
  local exe="$1"
  "$exe" - <<'PY'
import json
import platform
import sys

print(json.dumps({
    "version": f"{sys.version_info.major}.{sys.version_info.minor}",
    "arch": platform.architecture()[0],
    "machine": platform.machine(),
    "executable": sys.executable,
}))
PY
}

python_field() {
  local exe="$1"
  local field="$2"
  "$exe" - "$field" <<'PY'
import json
import platform
import sys

field = sys.argv[1]
info = {
    "version": f"{sys.version_info.major}.{sys.version_info.minor}",
    "arch": platform.architecture()[0],
    "machine": platform.machine(),
    "executable": sys.executable,
}
print(info[field])
PY
}

is_compatible_python() {
  local exe="$1"
  local version arch machine system

  version="$(python_field "$exe" version 2>/dev/null || true)"
  arch="$(python_field "$exe" arch 2>/dev/null || true)"
  machine="$(python_field "$exe" machine 2>/dev/null || true)"
  system="$(uname -s)"

  if [[ "$arch" != "64bit" ]]; then
    return 1
  fi
  case "$version" in
    3.10|3.11|3.12) ;;
    *) return 1 ;;
  esac

  if [[ "$system" == "Darwin" && "$machine" != "arm64" ]]; then
    echo "Unsupported macOS architecture: $machine. This skill pins paddlepaddle==3.2.2, which has macOS arm64 wheels but not macOS x86_64 wheels." >&2
    return 1
  fi

  return 0
}

resolve_python() {
  local candidates=(
    "python${PYTHON_VERSION}"
    "python3.12"
    "python3.11"
    "python3.10"
    "python3"
    "python"
  )

  local seen=" "
  for exe in "${candidates[@]}"; do
    if [[ "$seen" == *" $exe "* ]]; then
      continue
    fi
    seen="$seen$exe "
    if command -v "$exe" >/dev/null 2>&1 && is_compatible_python "$exe"; then
      command -v "$exe"
      return 0
    fi
  done

  if [[ "$DISABLE_UV_FALLBACK" != "1" ]] && command -v uv >/dev/null 2>&1; then
    for version in 3.12 3.11 3.10; do
      local found
      found="$(uv python find --managed-python --no-project "$version" 2>/dev/null || true)"
      if [[ -z "$found" ]]; then
        echo "Installing Python $version with uv because no compatible system Python was found." >&2
        run_checked uv python install "$version"
        found="$(uv python find --managed-python --no-project "$version" 2>/dev/null || true)"
      fi
      if [[ -n "$found" ]] && is_compatible_python "$found"; then
        echo "$found"
        return 0
      fi
    done
  fi

  echo "No compatible Python found. Install 64-bit Python 3.10, 3.11, or 3.12 and rerun setup.sh." >&2
  return 1
}

PYTHON_EXE="$(resolve_python)"
echo "Using Python: $(python_info_json "$PYTHON_EXE")"

if [[ -d "$VENV_PATH" ]]; then
  VENV_PYTHON="$VENV_PATH/bin/python"
  if [[ ! -x "$VENV_PYTHON" ]] || ! is_compatible_python "$VENV_PYTHON"; then
    echo "Removing incompatible skill-local virtual environment: $VENV_PATH"
    rm -rf "$VENV_PATH"
  fi
fi

if [[ ! -d "$VENV_PATH" ]]; then
  run_checked "$PYTHON_EXE" -m venv "$VENV_PATH"
fi

VENV_PYTHON="$VENV_PATH/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Virtual environment python was not created at $VENV_PYTHON" >&2
  exit 1
fi

run_checked "$VENV_PYTHON" -m pip install --upgrade pip

if [[ "$SKIP_INSTALL" != "1" ]]; then
  run_checked "$VENV_PYTHON" -m pip install --only-binary=:all: -r "$SCRIPT_DIR/requirements.txt"
fi

run_checked "$VENV_PYTHON" "$SCRIPT_DIR/doctor.py"
