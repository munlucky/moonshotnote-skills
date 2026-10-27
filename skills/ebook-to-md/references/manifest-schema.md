# ebook-to-md Manifest Schema

## `capture-manifest.json`

```json
{
  "schemaVersion": 1,
  "bookTitle": "unknown",
  "sourceUrl": "https://ebook.example/viewer",
  "captureStartedAt": "2026-05-04T14:00:00+09:00",
  "captureFinishedAt": "2026-05-04T14:10:00+09:00",
  "turnKey": "ArrowRight",
  "waitMs": 700,
  "viewport": {
    "width": null,
    "height": null
  },
  "pages": [
    {
      "pageIndex": 1,
      "imagePath": "captures/page-0001.png",
      "textPath": null,
      "method": "capture",
      "hash": "sha256:...",
      "url": "https://ebook.example/viewer",
      "title": "Book title",
      "warnings": []
    }
  ],
  "warnings": []
}
```

Required page fields:

- `pageIndex`: 1-based page order.
- `imagePath`: path relative to the run directory, or `null` for structured-only pages.
- `textPath`: path relative to the run directory, or `null` before extraction/OCR.
- `method`: `structured`, `capture`, `ocr`, or `mixed`.
- `hash`: content hash for screenshot pages, preferably `sha256:<hex>`.
- `url`: browser URL observed at capture time.
- `warnings`: page-specific QA warnings.

## `ocr-manifest.json`

```json
{
  "schemaVersion": 1,
  "language": "kor+eng",
  "inputDir": "captures",
  "outputDir": "ocr",
  "pages": [
    {
      "pageIndex": 1,
      "imagePath": "captures/page-0001.png",
      "ocrMarkdownPath": "ocr/page-0001.md",
      "ocrJsonPath": "ocr/page-0001.json",
      "confidence": null,
      "preprocessing": [],
      "warnings": []
    }
  ],
  "warnings": []
}
```

## Final Outputs

- `book.md`: final merged Markdown in reading order.
- `capture-report.md`: capture QA summary and page warnings.
- `ocr-report.md`: OCR confidence and failure summary when OCR runs.
- `inspect-report.json`: browser inspection output used to decide structured extraction vs capture.

Keep schemas additive. Do not rename existing fields without a migration note in the skill instructions.
