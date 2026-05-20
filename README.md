# moonshotnote-ocr

`moonshotnote-ocr` is a Codex-compatible Agent Skill for screenshot and document-image OCR, with a Korean-first PaddleOCR path and a Surya path for document layout, reading order, and table-heavy pages.

## Install

From a published GitHub repository:

```powershell
npx skills add <owner>/<repo> --skill moonshotnote-ocr -g -a codex -y
```

For local development from this checkout:

```powershell
npx skills add . --skill moonshotnote-ocr -g -a codex -y --copy
```

## Setup

The skill intentionally does not bundle OCR models or heavy Python dependencies. Install them into the installed skill's local virtual environment.

After `npx skills add`:

```powershell
cd $HOME\.agents\skills\moonshotnote-ocr
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

From a repository checkout:

```powershell
cd skills\moonshotnote-ocr
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

The setup script prefers 64-bit Python 3.10 through `py -3.10`, accepts 64-bit Python 3.11 or 3.12 as fallback, creates `.venv`, installs pinned PaddlePaddle/PaddleOCR/Surya versions from binary wheels, then runs `scripts\doctor.py`. It rejects 32-bit Python because OCR dependencies otherwise fall back to fragile local source builds. If `uv` is available and no compatible system Python exists, setup installs a uv-managed 64-bit Python runtime for the skill.

## Usage

```powershell
.\.venv\Scripts\python.exe scripts\ocr_image.py C:\path\to\screenshot.png --engine paddle --lang korean
```

Batch OCR cropped screenshots:

```powershell
.\.venv\Scripts\python.exe scripts\ocr_image.py C:\path\to\captures --pattern *-crop.png --engine paddle --lang korean --summary
```

Automatic engine selection:

```powershell
.\.venv\Scripts\python.exe scripts\ocr_image.py C:\path\to\page.png --engine auto --lang korean
```

Outputs:

```text
<input-dir>/ocr-output/<engine>/
  screenshot.paddle.txt
```

Default output is `.txt` only. Use `--json` for structured OCR evidence, `--md` for a review report, `--summary` for `batch_summary.json`, or `--all` to write every output.

Batch behavior:

- Continues processing later images when one image fails.
- Returns a non-zero exit code if any item failed.
- Use `--fail-fast` when the first failure should stop the batch immediately.

## Engine Policy

- Use PaddleOCR first for normal screenshots, UI captures, signs, receipts, and Korean or mixed Korean-English images.
- Use Surya for document pages where reading order, table structure, formulas, or markdown reconstruction matter.
- Use a PDF skill for PDF extraction and page rendering. This skill only handles image inputs or already-rendered scanned pages.

## Dependency Licenses

The skill scripts are MIT licensed. Runtime OCR dependencies keep their own licenses. In particular, `surya-ocr` is GPL-3.0-or-later, so review dependency licensing before bundling this skill into proprietary redistributed products. See `THIRD_PARTY_NOTICES.md`.

## Validation

```powershell
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\moonshotnote-ocr
npx skills add . --skill moonshotnote-ocr -g -a codex -y --copy
npx skills ls -g --json
```

Release checklist:

```powershell
npx -y skills add . --list
npx -y skills add <owner>/<repo> --skill moonshotnote-ocr --list
```

The GitHub Actions workflow in `.github/workflows/validate.yml` runs lightweight publish checks only: manifest validation, Python syntax compilation, and `npx skills add . --list`. It intentionally does not install PaddleOCR, Surya, or model files.
