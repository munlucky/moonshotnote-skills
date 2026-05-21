---
name: moonshotnote-ocr
description: Extract and verify OCR text from images, screenshots, scanned pages, Korean or mixed Korean-English UI captures, receipts, signs, document images, tables, and layout-heavy captures. Use PaddleOCR first for normal screenshots and Korean image OCR; use Surya when document layout, reading order, tables, formulas, or markdown reconstruction matter. Use the low-confidence review workflow when OCR output contains [unclear], suspicious lines, or low confidence scores, so Codex checks image evidence before closing.
---

# moonshotnote-ocr

Use this skill to extract reliable OCR from image files and scanned page images.

## Engine Choice

- Use PaddleOCR first for normal screenshots, UI captures, receipts, signs, mobile captures, Korean text, and mixed Korean-English text.
- Use Surya when the input is a document page where layout, reading order, tables, section headers, or formulas matter.
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

## Low-confidence Review

Do not treat a low-confidence count as a final result by itself.

When OCR output has `[unclear]`, low-confidence lines, suspicious mixed Korean/English text, table noise, code noise, or visible OCR artifacts:

1. Generate evidence outputs with `--json` or `--all`.
2. Build a review pack:

```powershell
.\.venv\Scripts\python.exe scripts/review_low_confidence.py C:\path\to\ocr-output\paddle --threshold 0.75
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

Run setup once on macOS Apple Silicon or Linux:

```bash
bash scripts/setup.sh
```

Check the local runtime:

```powershell
.\.venv\Scripts\python.exe scripts/doctor.py
```

On macOS/Linux:

```bash
./.venv/bin/python scripts/doctor.py
```

OCR an image with PaddleOCR Korean mode:

```powershell
.\.venv\Scripts\python.exe scripts/ocr_image.py C:\path\to\screenshot.png --engine paddle --lang korean
```

OCR a directory of cropped screenshots:

```powershell
.\.venv\Scripts\python.exe scripts/ocr_image.py C:\path\to\captures --pattern *-crop.png --engine paddle --lang korean --summary
```

Use automatic engine selection:

```powershell
.\.venv\Scripts\python.exe scripts/ocr_image.py C:\path\to\page.png --engine auto --lang korean
```

Create a visual low-confidence review pack:

```powershell
.\.venv\Scripts\python.exe scripts/review_low_confidence.py C:\path\to\ocr-output\paddle --threshold 0.75
```

## Verification Policy

After OCR, report:

- engine used
- output files written
- low-confidence review pack path, if low-confidence items exist
- reviewed status counts: accepted, corrected, unreadable, ignored, needs_review
- whether fallback was used

If `needs_review` is not zero, say clearly that OCR verification is not fully closed. Do not imply the text is final.

For normal screenshots, group extracted UI text by title, navigation, buttons, labels, body text, warning/error messages, and footer when the visual structure makes that classification clear.
