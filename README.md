# moonshotnote-skills

Public Codex-compatible Agent Skills maintained under the `moonshotnote-skills` repository.

- `moonshotnote-ocr`: Korean-first screenshot and document-image OCR with PaddleOCR, Surya, and low-confidence visual review.
- `fastapi-clean-architecture`: public-safe FastAPI and clean architecture knowledge graph extracted from verified OCR notes.
- `text-knowledge-skill-builder`: reusable workflow for turning source text into public-safe knowledge-backed skills.

## Install

From a published GitHub repository:

```powershell
npx skills add munlucky/moonshotnote-skills --skill moonshotnote-ocr -g -a codex -y
npx skills add munlucky/moonshotnote-skills --skill fastapi-clean-architecture -g -a codex -y
npx skills add munlucky/moonshotnote-skills --skill text-knowledge-skill-builder -g -a codex -y
```

For local development from this checkout:

```powershell
npx skills add . --skill moonshotnote-ocr -g -a codex -y --copy
npx skills add . --skill fastapi-clean-architecture -g -a codex -y --copy
npx skills add . --skill text-knowledge-skill-builder -g -a codex -y --copy
```

## moonshotnote-ocr Setup

The skill intentionally does not bundle OCR models or heavy Python dependencies. Install them into the installed skill's local virtual environment.

Supported local setup targets:

- Windows x64 with Python 3.10, 3.11, or 3.12
- macOS Apple Silicon arm64 with Python 3.10, 3.11, or 3.12
- Linux x64 with Python 3.10, 3.11, or 3.12

macOS Intel x86_64 is not supported by the pinned `paddlepaddle==3.2.2` runtime because the matching macOS x86_64 wheel is not published.

After `npx skills add`:

```powershell
cd $HOME\.agents\skills\moonshotnote-ocr
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

On macOS Apple Silicon or Linux:

```bash
cd ~/.agents/skills/moonshotnote-ocr
bash scripts/setup.sh
```

From a repository checkout:

```powershell
cd skills\moonshotnote-ocr
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

On macOS Apple Silicon or Linux from a repository checkout:

```bash
cd skills/moonshotnote-ocr
bash scripts/setup.sh
```

The setup scripts create `.venv`, install pinned PaddlePaddle/PaddleOCR/Surya versions from binary wheels, then run `scripts/doctor.py`. They reject unsupported Python or CPU combinations because OCR dependencies otherwise fall back to fragile local source builds. If `uv` is available and no compatible system Python exists, setup installs a uv-managed Python runtime for the skill.

## moonshotnote-ocr Usage

```powershell
.\.venv\Scripts\python.exe scripts\ocr_image.py C:\path\to\screenshot.png --engine paddle --lang korean
```

macOS/Linux:

```bash
./.venv/bin/python scripts/ocr_image.py ~/Desktop/screenshot.png --engine paddle --lang korean
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

Low-confidence visual review:

```powershell
.\.venv\Scripts\python.exe scripts\ocr_image.py C:\path\to\screenshot.png --engine paddle --lang korean --json
.\.venv\Scripts\python.exe scripts\review_low_confidence.py C:\path\to\ocr-output\paddle --threshold 0.75
```

The review script creates crop images, contact sheets, `low_confidence_manifest.json`, and `low_confidence_review.md`. Do not treat OCR as fully verified while manifest items remain `needs_review`.

Batch behavior:

- Continues processing later images when one image fails.
- Returns a non-zero exit code if any item failed.
- Use `--fail-fast` when the first failure should stop the batch immediately.

## Engine Policy

- Use PaddleOCR first for normal screenshots, UI captures, signs, receipts, and Korean or mixed Korean-English images.
- Use Surya for document pages where reading order, table structure, formulas, or markdown reconstruction matter.
- Use a PDF skill for PDF extraction and page rendering. This skill only handles image inputs or already-rendered scanned pages.

## fastapi-clean-architecture Usage

The FastAPI skill does not bundle the full OCR text. It ships a public-safe graph and helper scripts:

```powershell
py -3 skills\fastapi-clean-architecture\scripts\query_graph.py --q "FastAPI Depends 의존성 주입" --json
py -3 skills\fastapi-clean-architecture\scripts\expand_context.py --q "회원가입 유스케이스" --out skills\fastapi-clean-architecture\output\source-pack.md
py -3 skills\fastapi-clean-architecture\scripts\validate_graph.py skills\fastapi-clean-architecture\references
```

For local private source metadata, run `prepare_private_source.py` with the reviewed OCR text and low-confidence review closeout. Its outputs are written under `skills/fastapi-clean-architecture/output/private-source/`, which is ignored by git.

## text-knowledge-skill-builder Usage

Use this skill when turning long source text into a reusable Skill:

```powershell
py -3 skills\text-knowledge-skill-builder\scripts\chunk_source_text.py --source <source.txt> --out-dir skills\<target-skill>\output\private-source
py -3 skills\text-knowledge-skill-builder\scripts\lint_knowledge_pack.py skills\<target-skill>\references
py -3 skills\text-knowledge-skill-builder\scripts\audit_public_safety.py skills\<target-skill>
```

The workflow is `text -> knowledge -> skill`: private source chunks stay ignored under `output/`, while public Skill references contain summaries, graph relations, provenance, and validation scripts.

## Dependency Licenses

The skill scripts are MIT licensed. Runtime OCR dependencies keep their own licenses. In particular, `surya-ocr` is GPL-3.0-or-later, so review dependency licensing before bundling this skill into proprietary redistributed products. See `THIRD_PARTY_NOTICES.md`.

## Validation

```powershell
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\moonshotnote-ocr
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\fastapi-clean-architecture
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\text-knowledge-skill-builder
py -3 skills\fastapi-clean-architecture\scripts\validate_graph.py skills\fastapi-clean-architecture\references
py -3 skills\text-knowledge-skill-builder\scripts\lint_knowledge_pack.py skills\fastapi-clean-architecture\references
py -3 skills\text-knowledge-skill-builder\scripts\audit_public_safety.py skills\fastapi-clean-architecture
npx skills add . --skill moonshotnote-ocr -g -a codex -y --copy
npx skills add . --skill fastapi-clean-architecture -g -a codex -y --copy
npx skills add . --skill text-knowledge-skill-builder -g -a codex -y --copy
npx skills ls -g --json
```

Release checklist:

```powershell
npx -y skills add . --list
npx -y skills add munlucky/moonshotnote-skills --skill moonshotnote-ocr --list
npx -y skills add munlucky/moonshotnote-skills --skill fastapi-clean-architecture --list
npx -y skills add munlucky/moonshotnote-skills --skill text-knowledge-skill-builder --list
```

The GitHub Actions workflow in `.github/workflows/validate.yml` runs lightweight publish checks only: manifest validation, Python syntax compilation, and `npx skills add . --list`. It intentionally does not install PaddleOCR, Surya, or model files.
