---
name: moonshotnote-ocr
description: Extract OCR text from images, screenshots, scanned pages, Korean or mixed Korean-English UI captures, receipts, signs, document images, tables, and layout-heavy captures. Use PaddleOCR first for normal screenshots and Korean image OCR; use Surya when document layout, reading order, tables, formulas, or markdown reconstruction matter. For scanned PDFs, use a PDF skill to convert pages to images first, then use this skill for OCR.
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

## Verification Policy

After OCR, report:

- engine used
- output files written
- low-confidence or suspicious lines, if available
- whether fallback was used

For normal screenshots, group extracted UI text by title, navigation, buttons, labels, body text, warning/error messages, and footer when the visual structure makes that classification clear.
