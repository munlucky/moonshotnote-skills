# Handoff

Status: implementation complete for target-scope code and docs.

## What Changed

- Added `skills/moonshotnote-ocr/scripts/ocr_pipeline/` with canonical models, engine adapters, router, classifier, postprocess helpers, and output writer.
- Replaced `ocr_image.py` with a thin CLI entrypoint that preserves existing options and adds `--engine pp-structure` plus `--page-mode`.
- Updated `doctor.py` to report required imports separately from optional PP-StructureV3 capability.
- Added model-free tests for canonical schema, page classification, and low-confidence review compatibility.
- Updated `SKILL.md`, `agents/openai.yaml`, and root `README.md`.
- Added plan package closeout artifacts and `phase-status.yaml`.

## Continue From Here

1. Install the skill-local OCR runtime:

```powershell
cd skills\moonshotnote-ocr
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

2. Run the local runtime doctor:

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py
```

3. Run local OCR smoke with real ebook capture samples:

```powershell
.\.venv\Scripts\python.exe scripts\ocr_image.py C:\path\to\plain.png --engine paddle --page-mode auto --json
.\.venv\Scripts\python.exe scripts\ocr_image.py C:\path\to\table.png --engine auto --page-mode auto --json
.\.venv\Scripts\python.exe scripts\ocr_image.py C:\path\to\multi-column.png --engine auto --page-mode auto --json
```

4. If PP-StructureV3 remains unavailable, keep it documented as optional unavailable and rely on Paddle/Surya paths.
