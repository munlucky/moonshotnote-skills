---
name: ebook-to-md
description: Orchestrate browser-based ebook conversion to Markdown by combining agent-browser page inspection, structured DOM/iframe text extraction, screenshot capture, capture QA, batch OCR via ocr-document-processor, and final book.md assembly. Use when Codex needs to convert a web EPUB reader, browser ebook viewer, paginated online book, iframe/canvas ebook, or screenshot/OCR fallback workflow into Markdown or text.
---

# ebook-to-md

## Overview

Use this skill to turn an accessible browser ebook into ordered Markdown. Prefer structured text from DOM, iframe, accessibility snapshot, or viewer APIs; fall back to screenshots only when structured extraction is not sufficient. Never run OCR inside the page-turn capture loop; finish capture and QA first, then OCR the approved image set in batch.

Only process content the user is authorized to access. Do not bypass DRM, authentication, paywalls, copy restrictions, or technical access controls. If a site blocks extraction, use the visible browser surface only when the user has access and the task is lawful.

## Prerequisites

Before controlling a browser, check the installed command surface:

```bash
agent-browser skills get core
```

Install the dependent skills and browser engine if they are missing:

```bash
npx skills add https://github.com/vercel-labs/agent-browser --skill agent-browser
npx skills add https://github.com/dkyazzentwatwa/chatgpt-skills --skill ocr-document-processor
npm install -g agent-browser
agent-browser doctor --offline --quick
```

Run `agent-browser install` only when `doctor` cannot find a usable Chrome or Chromium. On macOS, system Google Chrome is sufficient when `doctor` passes.

## Workflow

1. Inspect the open ebook with `scripts/ebook_inspect.py`; save `inspect-report.json`.
2. Use structured extraction if the report shows enough stable body text from DOM, iframe, accessibility snapshot, or viewer APIs.
3. If structured extraction is insufficient, capture every page with `scripts/ebook_capture_all.py`; use a bounded `--max-pages` during smoke tests.
4. Validate captures with `scripts/ebook_capture_qa.py`; fix duplicate, blank, loading, or missing pages before OCR.
5. Run `scripts/ebook_ocr_batch.py` after QA; it delegates OCR to `ocr-document-processor` instead of reimplementing OCR.
6. Assemble `book.md` with `scripts/ebook_assemble_md.py` from structured text and OCR Markdown.

Read `references/pipeline.md` when choosing extraction vs capture behavior, viewer detection heuristics, or end-of-book detection. Read `references/manifest-schema.md` before changing manifest fields or output names.

## Commands

Inspect:

```bash
python3 scripts/ebook_inspect.py --output ./ebook-run --lang kor+eng --max-pages 5 --wait-ms 700 --turn-key ArrowRight
```

Capture a bounded sample:

```bash
python3 scripts/ebook_capture_all.py --output ./ebook-run --max-pages 5 --wait-ms 700 --turn-key ArrowRight
```

Validate captures:

```bash
python3 scripts/ebook_capture_qa.py --input ./ebook-run/capture-manifest.json --output ./ebook-run --lang kor+eng --max-pages 5 --wait-ms 700 --turn-key ArrowRight
```

Run OCR batch:

```bash
python3 scripts/ebook_ocr_batch.py --input ./ebook-run/captures --output ./ebook-run --lang kor+eng --max-pages 0 --wait-ms 700 --turn-key ArrowRight
```

The wrapper calls the installed `ocr-document-processor/scripts/ocr_processor.py` twice, once for Markdown and once for JSON, because that CLI accepts one `--format` value per run.

Assemble Markdown:

```bash
python3 scripts/ebook_assemble_md.py --input ./ebook-run --output ./ebook-run --lang kor+eng --max-pages 0 --wait-ms 700 --turn-key ArrowRight
```

All scripts support `--dry-run`, `--input`, `--output`, `--lang`, `--max-pages`, `--wait-ms`, and `--turn-key`. Use `--dry-run` before long captures.

## Output Contract

Write outputs under a run directory:

- `inspect-report.json`
- `capture-manifest.json`
- `captures/page-0001.png`
- `capture-report.md`
- `ocr/` and `ocr-manifest.json` when OCR runs
- `book.md`
