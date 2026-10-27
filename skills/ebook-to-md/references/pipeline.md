# ebook-to-md Pipeline

## Stages

1. Inspect
   - Run `agent-browser skills get core` and follow the installed command shape.
   - Capture URL, title, accessibility snapshot, `body` text, `body` HTML, iframe inventory, canvas/image counts, and common EPUB/Readium markers.
   - Decide whether structured extraction is likely to be better than OCR.

2. Structured extract
   - Prefer DOM text when it is long enough, changes after page turns, and does not include only menus or chrome.
   - Try iframe text when same-origin access is available.
   - Check common viewer globals such as `ePub`, `rendition`, `Readium`, or app-specific reader containers.
   - Save page-aligned text files and mark manifest pages with `method: "structured"` when this path succeeds.

3. Capture all
   - Use screenshot capture only when structured text is unavailable, duplicated, too short, or clearly missing content.
   - Capture first, hash, record metadata, then press the turn key and wait.
   - Do not OCR during this loop.
   - Use bounded `--max-pages` for smoke tests; choose an explicit larger bound for full books.

4. Validate captures
   - Flag duplicate hashes, tiny files, missing files, inconsistent dimensions, repeated URLs, and repeated titles.
   - Treat repeated screenshots after a page turn as a likely last-page or blocked-navigation signal.
   - Treat very small screenshots as blank/loading failures.
   - Re-capture bad pages before OCR.

5. OCR batch
   - Run `ocr-document-processor` only after capture QA passes.
   - Keep OCR outputs page-aligned by filename, for example `page-0001.md` and `page-0001.json`.
   - Record confidence and preprocessing warnings in `ocr-manifest.json` when available.

6. Assemble Markdown
   - Merge structured text first, OCR Markdown second.
   - Preserve page order from `capture-manifest.json`.
   - Insert page comments only when useful for troubleshooting; avoid noisy page headers in the final book.

## Viewer Heuristics

- EPUB.js: look for `window.ePub`, `window.rendition`, `.epub-container`, `.epub-view`, or iframe-based spine items.
- Readium: look for `readium`, `Readium`, `navigator.epubReadingSystem`, iframe spine documents, or `epubReadingSystem` metadata.
- iframe viewer: enumerate iframes with source URL, size, and same-origin text access. Prefer the largest readable iframe.
- Canvas/image-only viewer: expect little DOM text, many canvas/image nodes, or screenshots that contain the real page content. Use capture and OCR.
- PDF-like web viewer: detect page canvases/images and page counters. Treat as capture-first unless selectable text is available.

## End-of-Book Signals

- Consecutive screenshot hash repeats after a page-turn command.
- URL, title, and body text all repeat after a page-turn command.
- Viewer exposes a disabled next button or final page counter.
- Accessibility snapshot no longer changes after page-turn commands.

Do not rely on one signal for full runs. Stop automatically only when screenshot hash repeats or an explicit `--max-pages` bound is reached; otherwise record warnings for manual review.

## Quality Rules

- Never skip QA before OCR.
- Never declare low-confidence OCR as exact text.
- Keep the original screenshots until the final Markdown is accepted.
- Re-run OCR only for failed or low-confidence pages when possible.
