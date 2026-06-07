# Phase 2: Canonical OCR schema

Status: ready
Depends-On: Phase 1

## Goal

Introduce an internal canonical OCR model so PaddleOCR, PP-StructureV3, and Surya output can preserve the existing JSON/review contract.

## Owned Paths

- `skills/moonshotnote-ocr/scripts/ocr_image.py`
- `skills/moonshotnote-ocr/scripts/ocr_pipeline/__init__.py`
- `skills/moonshotnote-ocr/scripts/ocr_pipeline/models.py`
- `skills/moonshotnote-ocr/scripts/ocr_pipeline/engines/paddle.py`
- `skills/moonshotnote-ocr/scripts/ocr_pipeline/engines/pp_structure.py`
- `skills/moonshotnote-ocr/scripts/ocr_pipeline/engines/surya.py`
- `skills/moonshotnote-ocr/scripts/ocr_pipeline/output.py`
- `skills/moonshotnote-ocr/tests/fixtures/**` if committed fixture data is added
- `skills/moonshotnote-ocr/tests/test_canonical_schema.py` if a test harness is added

## Read-Only Paths

- `skills/moonshotnote-ocr/scripts/review_low_confidence.py` behavior contract
- `skills/moonshotnote-ocr/scripts/setup.ps1`
- `skills/moonshotnote-ocr/scripts/setup.sh`
- `README.md`
- `.github/workflows/validate.yml` unless only py_compile paths are added in a later phase
- Generated OCR/review/model/cache outputs

## Work

- Keep `ocr_image.py` as the CLI entrypoint and move engine execution/normalization/writing logic into `ocr_pipeline`.
- Leave argparse-compatible options in `ocr_image.py`; do not remove existing flags.
- Define canonical dataclasses or typed dictionaries for OCR item, structured page, runtime metadata, and OCR result.
- Preserve existing JSON keys and types: `engine`, `input`, `text`, `items`, `warnings`, `low_confidence`.
- Add only optional fields: `requested_engine`, `fallback_used`, `fallback_reason`, `page_type`, `page_type_confidence`, `runtime_metadata`, `structured`.
- Normalize PaddleOCR output into canonical `items[]`.
- Normalize Surya output into canonical `items[]` where available.
- If Phase 1 is Go, normalize PP-StructureV3 output into canonical `items[]` and `structured.tables/layout_blocks/markdown`.
- If Phase 1 is No-go, add a stub adapter that returns an explicit capability error without changing other engine paths.

## Contract Details

- `box` uses original image coordinates and may be polygon or axis-aligned bbox.
- `source_span` is metadata only; it must not replace `text`, `confidence`, or `box`.
- `reading_order` is a numeric order in the normalized output sequence.
- Canonical `text` is built from canonical `items[]` unless an explicit structured markdown output is requested in a later phase.

## Acceptance Evidence

- Golden JSON fixture for existing Paddle output retains old keys.
- Golden JSON fixture for Surya-like output retains old keys.
- PP-Structure fixture is either normalized to canonical shape or records explicit unavailable capability.
- `review_low_confidence.py` can still read `payload.input` and `items[].text/confidence/box`.
- `py_compile` passes for `ocr_image.py` and all new `ocr_pipeline` modules.

## Rollback

Keep `ocr_image.py` public behavior unchanged and remove the new package import path if canonical model integration fails.
