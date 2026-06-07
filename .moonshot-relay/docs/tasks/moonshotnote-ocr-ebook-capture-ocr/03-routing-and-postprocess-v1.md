# Phase 3: Routing and postprocess

Status: ready
Depends-On: Phase 2

## Goal

Add deterministic page-type classification, engine routing, and postprocessing on top of the canonical schema.

## Owned Paths

- `skills/moonshotnote-ocr/scripts/ocr_pipeline/classifiers/page_type.py`
- `skills/moonshotnote-ocr/scripts/ocr_pipeline/router.py`
- `skills/moonshotnote-ocr/scripts/ocr_pipeline/postprocess/paragraphs.py`
- `skills/moonshotnote-ocr/scripts/ocr_pipeline/postprocess/columns.py`
- `skills/moonshotnote-ocr/scripts/ocr_pipeline/postprocess/tables.py`
- `skills/moonshotnote-ocr/scripts/ocr_image.py` for CLI enum wiring only
- `skills/moonshotnote-ocr/tests/test_page_type.py`
- `skills/moonshotnote-ocr/tests/test_router.py`

## Read-Only Paths

- Phase 2 canonical model definitions except additive fields needed by router/postprocess
- `skills/moonshotnote-ocr/scripts/review_low_confidence.py`
- Setup scripts and dependency pins
- Generated output directories

## CLI Contract

```text
--engine auto|paddle|pp-structure|surya
--page-mode auto|plain-text|table|multi-column|layout|unknown
```

Routing rules:

- `--engine paddle`: PaddleOCR only; never invoke Surya or PP-StructureV3.
- `--engine surya`: Surya only; fail with capability error if unavailable.
- `--engine pp-structure`: PP-StructureV3 only; fail with capability error if unavailable.
- `--engine auto`: run PaddleOCR first, classify the canonical result, then apply deterministic fallback rules.

Fallback rules:

- Paddle exception or empty text: use Surya if available; otherwise return Paddle failure with explicit warning.
- `page_type=table` and PP-StructureV3 available: rerun with PP-StructureV3.
- `page_type=multi-column` or `layout` and Surya available: rerun with Surya.
- Optional engine unavailable: keep Paddle output and add `fallback_reason`.
- No silent engine switch.

## Page Type Contract

Enum: `plain-text`, `table`, `multi-column`, `layout`, `unknown`.

Classifier input is canonical PaddleOCR `items[]`, not PP-Structure or Surya output.

Score components to record:

- `table_score`
- `column_score`
- `layout_score`
- `median_confidence`
- `text_density`

The implementation must document thresholds in `page_type.py`; tests may use synthetic boxes so they do not require OCR models.

## Output Examples

Default auto path:

```text
<input-dir>/ocr-output/auto/<stem>.paddle.txt
<input-dir>/ocr-output/auto/<stem>.paddle.json
```

Auto fallback to Surya:

```json
{
  "requested_engine": "auto",
  "engine": "surya",
  "fallback_used": true,
  "fallback_reason": "page_type=multi-column"
}
```

Explicit `--out C:\tmp\out` writes inside the provided out directory and preserves the existing relative-parent behavior for batch inputs.

## Acceptance Evidence

- Unit tests for plain-text/table/multi-column/layout/unknown classifier outputs.
- Golden JSON for `auto -> paddle`, `auto -> surya`, and PP-Structure unavailable warning.
- Existing empty/fail fallback to Surya remains covered.
- Batch summary includes requested engine, actual engine, fallback status, warnings, and output paths.

## Rollback

Disable `auto` page-type fallback behind explicit warning and retain Paddle-first behavior if classifier confidence is unreliable.
