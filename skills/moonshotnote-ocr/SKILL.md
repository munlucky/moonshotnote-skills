---
name: moonshotnote-ocr
description: Extract and verify OCR text from images, screenshots, scanned pages, Korean or mixed Korean-English UI captures, receipts, signs, ebook captures, document images, tables, and layout-heavy captures. Use PaddleOCR first for normal screenshots and Korean image OCR; use page-mode auto for ebook pages; use optional PP-StructureV3 when available for table pages; use Surya when document layout, reading order, formulas, or complex markdown reconstruction matter. Use the low-confidence review workflow when OCR output contains [unclear], suspicious lines, or low confidence scores, so Codex checks image evidence before closing.
---

# moonshotnote-ocr

Use this skill to extract reliable OCR from image files and scanned page images.

## Engine Choice

- Use PaddleOCR first for normal screenshots, UI captures, receipts, signs, mobile captures, Korean text, and mixed Korean-English text.
- Use `--page-mode auto` for ebook captures so PaddleOCR boxes can classify `plain-text`, `table`, `multi-column`, `layout`, or `unknown`.
- Use optional PP-StructureV3 only when `doctor.py` reports `optional_capabilities.pp_structure.available=true`; it is intended for table/layout parsing and may be unavailable on a local runtime.
- Use Surya when the input is a document page where layout, reading order, section headers, formulas, or markdown reconstruction matter.
- Use `--engine paddle` when the task must avoid Surya runtime use.
- For PDFs, do not reimplement PDF handling here. If text is selectable, use a PDF skill. If scanned, convert pages to images with a PDF skill, then run this skill on the page images.

## Output Policy

Default output is intentionally minimal:

- plain text: `<stem>.<engine>.txt`

When `--out` is not provided, save under the source location: `<input-dir>/ocr-output/<engine>/`.

Use optional evidence outputs only when needed:

- `--json`: write `<stem>.<engine>.json` with boxes, confidence, warnings, and low-confidence lines
- `--md`: write `<stem>.<engine>.md` for human review
- `--summary`: write `batch_summary.json` for batch audit
- `--all`: write txt, json, md, and batch summary

Preserve original text. Do not translate Korean unless the user asks for translation. Mark unreadable or suspicious text as `[unclear]` rather than inventing content.

Structured JSON fields are additive. Existing consumers can keep reading `engine`, `input`, `text`, `items`, `warnings`, and `low_confidence`. New outputs may also include `requested_engine`, `fallback_used`, `fallback_reason`, `page_type`, `page_type_confidence`, `runtime_metadata`, and `structured`.

## Low-confidence Review

Do not treat a low-confidence count as a final result by itself.

When OCR output has `[unclear]`, low-confidence lines, suspicious mixed Korean/English text, table noise, code noise, or visible OCR artifacts:

1. Generate evidence outputs with `--json` or `--all`.
2. Build a review pack:

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts/review_low_confidence.py C:\path\to\ocr-output\paddle --threshold 0.75
```

3. Inspect the generated crop images/contact sheets against the original page images.
4. Update `low_confidence_manifest.json` item statuses:
   - `accepted`: OCR text is good enough
   - `corrected`: `review_text` contains the corrected text
   - `unreadable`: source image is not legible enough to recover
   - `ignored`: non-content chrome, page number, watermark, decoration, or irrelevant table artifact
5. Do not close the task while any item remains `needs_review` unless the user explicitly accepts that risk.

If there are many low-confidence items, prioritize content-bearing body text, headings, code, table labels, and commands first. Page numbers, viewer chrome, watermarks, tiny benchmark internals, and decorative glyphs can be marked `ignored` after visual confirmation.

## Commands

Run setup once on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

Default setup installs the PaddleOCR core runtime only. Install optional table/layout dependencies only when needed:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -InstallStructure
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -InstallSurya
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -InstallAll
```

By default, setup creates a shared runtime at `%MOONSHOT_RELAY_HOME%\runtimes\moonshotnote-ocr-py312`, or `%USERPROFILE%\.moonshot-relay\runtimes\moonshotnote-ocr-py312` when `MOONSHOT_RELAY_HOME` is unset. Set `MOONSHOTNOTE_OCR_RUNTIME` or pass `-RuntimePath` only when a custom shared runtime location is required.

Run setup once on macOS Apple Silicon or Linux:

```bash
bash scripts/setup.sh
```

On macOS Apple Silicon, keep the default setup path for PaddleOCR first. Optional dependencies can be requested explicitly:

```bash
bash scripts/setup.sh --with-structure
bash scripts/setup.sh --with-surya
bash scripts/setup.sh --with-all
```

macOS Intel x86_64 is not supported by the pinned PaddlePaddle runtime.

Check the local runtime:

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts/doctor.py
```

On macOS/Linux:

```bash
OCR_PYTHON="${MOONSHOT_RELAY_HOME:-$HOME/.moonshot-relay}/runtimes/moonshotnote-ocr-py312/bin/python"
"$OCR_PYTHON" scripts/doctor.py
```

OCR an image with PaddleOCR Korean mode:

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts/ocr_image.py C:\path\to\screenshot.png --engine paddle --lang korean
```

OCR a directory of cropped screenshots:

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts/ocr_image.py C:\path\to\captures --pattern *-crop.png --engine paddle --lang korean --summary
```

Use automatic engine selection:

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts/ocr_image.py C:\path\to\page.png --engine auto --lang korean
```

Use ebook page classification:

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts/ocr_image.py C:\path\to\ebook-page.png --engine auto --page-mode auto --lang korean --json
```

Force PaddleOCR only:

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts/ocr_image.py C:\path\to\page.png --engine paddle --page-mode auto --lang korean
```

Request PP-StructureV3 only when `doctor.py` reports it is available:

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts/ocr_image.py C:\path\to\table.png --engine pp-structure --page-mode table --json
```

Create a visual low-confidence review pack:

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts/review_low_confidence.py C:\path\to\ocr-output\paddle --threshold 0.75
```

## Verification Policy

After OCR, report:

- requested engine and actual engine used
- page type and whether fallback was used
- output files written
- low-confidence review pack path, if low-confidence items exist
- reviewed status counts: accepted, corrected, unreadable, ignored, needs_review
- whether fallback was used

If `needs_review` is not zero, say clearly that OCR verification is not fully closed. Do not imply the text is final.

For normal screenshots, group extracted UI text by title, navigation, buttons, labels, body text, warning/error messages, and footer when the visual structure makes that classification clear.
