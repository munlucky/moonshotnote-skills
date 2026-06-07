# QA Report

Date: 2026-06-07
Plan: `moonshotnote-ocr-ebook-capture-ocr`
Status: target-scope checks passed; local OCR runtime smoke not run because the active Python runtime is not the skill-local 64-bit OCR environment.

## Checks Run

```powershell
py -3 -m py_compile skills\moonshotnote-ocr\scripts\ocr_image.py skills\moonshotnote-ocr\scripts\doctor.py skills\moonshotnote-ocr\scripts\review_low_confidence.py
```

Result: pass.

```powershell
$files = Get-ChildItem skills\moonshotnote-ocr\scripts\ocr_pipeline -Recurse -Filter *.py | ForEach-Object { $_.FullName }
py -3 -m py_compile @files
```

Result: pass.

```powershell
py -3 -m unittest discover -s skills\moonshotnote-ocr\tests -p 'test_*.py'
```

Result: pass, 6 tests run, 1 skipped because Pillow is not installed in the active Python environment.

```powershell
$env:PYTHONUTF8='1'; py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\moonshotnote-ocr
```

Result: pass.

```powershell
npx -y skills add . --skill moonshotnote-ocr --list
```

Result: pass; `moonshotnote-ocr` is discoverable.

```powershell
py -3 skills\moonshotnote-ocr\scripts\ocr_image.py --help
```

Result: pass; help shows `--engine auto|paddle|pp-structure|surya` and `--page-mode auto|plain-text|table|multi-column|layout|unknown`.

```powershell
py -3 skills\moonshotnote-ocr\scripts\doctor.py
```

Result: expected runtime failure in current shell: Python is 32-bit and OCR dependencies are not installed. The JSON report still showed `optional_capabilities.pp_structure.available=false` with reason `paddleocr import failed: No module named 'paddleocr'`.

## Residual Risks

- Real PaddleOCR, PP-StructureV3, and Surya inference were not run because the active shell is not the skill-local 64-bit OCR runtime.
- PP-StructureV3 remains optional and unavailable until `scripts/setup.ps1` installs a compatible OCR environment and `doctor.py` reports it available.
- Existing repo-wide CI may still include non-OCR drift; target-scope skill discovery passed.
