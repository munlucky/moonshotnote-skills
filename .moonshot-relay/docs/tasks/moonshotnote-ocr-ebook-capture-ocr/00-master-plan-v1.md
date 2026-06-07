# moonshotnote-ocr ebook capture OCR plan

Last-Reviewed: 2026-06-07
Status: ready-for-phase-execution
Package Root: `.moonshot-relay/docs/tasks/moonshotnote-ocr-ebook-capture-ocr/`

## Objective

Improve `skills/moonshotnote-ocr` for ebook capture OCR without expanding scope into viewer UI crop preprocessing, VLM OCR, or Tesseract-first workflows.

The implementation must keep PaddleOCR as the default path, add page-type-aware structure handling, and preserve the existing low-confidence visual review contract.

## Package Inventory

- Master plan: `00-master-plan-v1.md`
- Phase 1: `01-runtime-dependency-spike-v1.md`
- Phase 2: `02-canonical-ocr-schema-v1.md`
- Phase 3: `03-routing-and-postprocess-v1.md`
- Phase 4: `04-docs-and-review-workflow-v1.md`
- Phase 5: `05-verification-closeout-v1.md`
- Review artifact: `planning-loop/plan-quality-review-iter-01.yaml`

## Decisions

- Existing output is additive-only: `engine`, `input`, `text`, `items`, `warnings`, `low_confidence`, txt/json/md/summary outputs must remain compatible.
- New structured metadata is additive: `requested_engine`, `fallback_used`, `fallback_reason`, `page_type`, `page_type_confidence`, `runtime_metadata`, and `structured`.
- Canonical `items[]` is the compatibility surface for all engines. Each item keeps `text`, `confidence`, `box`, and `raw`, and may add `source_engine`, `source_block_type`, `source_span`, and `reading_order`.
- `box` is always original-image coordinate data. It may be polygon or `[x1, y1, x2, y2]`; `review_low_confidence.py` must continue to normalize both forms.
- `--engine auto` keeps the requested output root behavior. Default output remains under `ocr-output/auto/`; per-image filenames may continue to use actual engine prefix as today.
- `requested_engine` records the CLI request; `engine` records the actual engine used for that image.
- PP-StructureV3 is an optional capability, not a guaranteed default route until Phase 1 proves `paddleocr[doc-parser]==3.4.1` or an approved equivalent works with `--only-binary=:all:`.
- If PP-StructureV3 cannot be installed or imported under the pinned policy, close it as `unavailable_with_reason`; keep PaddleOCR/Surya paths and do not silently ship a broken `pp-structure` route.
- `opencv-python` removal is out of scope. Do not add body crop or viewer UI removal preprocessing.
- Surya remains optional fallback. Documentation must state that `--engine paddle` avoids Surya runtime use.

## Public Interfaces

CLI additions:

```text
--engine auto|paddle|pp-structure|surya
--page-mode auto|plain-text|table|multi-column|layout|unknown
```

Required JSON shape additions:

```json
{
  "requested_engine": "auto",
  "engine": "paddle",
  "fallback_used": false,
  "fallback_reason": null,
  "page_type": "plain-text",
  "page_type_confidence": 0.91,
  "runtime_metadata": {
    "packages": {},
    "pipeline": "paddle",
    "model_settings": {},
    "device": null,
    "capabilities": {},
    "model_source": null,
    "cache_status": null
  },
  "structured": {
    "tables": [],
    "columns": [],
    "layout_blocks": [],
    "markdown": null
  }
}
```

Canonical item additions:

```json
{
  "text": "line text",
  "confidence": 0.97,
  "box": [[0, 0], [10, 0], [10, 10], [0, 10]],
  "raw": {},
  "source_engine": "paddle",
  "source_block_type": "text_line",
  "source_span": {"page": 1, "block_id": null, "line_id": null},
  "reading_order": 1
}
```

## Phase Dependencies

1. Phase 1 must run before PP-StructureV3 engine work.
2. Phase 2 owns canonical models, writers, and engine adapters.
3. Phase 3 may only add classifier/router/postprocess modules on top of Phase 2 models.
4. Phase 4 may update human-facing docs only after CLI/schema decisions are implemented.
5. Phase 5 verifies the full package and records any repo-wide blocker separately from OCR-specific checks.

## Global Read-Only And Non-Payload Paths

- Unrelated `skills/**`
- Generated `.venv/**`, `ocr-output/**`, `ocr_output/**`, `output/**`, review output folders, model caches, browser artifacts, sqlite state, memorygraph data, verdict JSON
- `C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py`
- Child-agent review outputs except parent-authored `planning-loop/plan-quality-review-iter-01.yaml`

## Known External Blocker

`.github/workflows/validate.yml` currently references removed trading skills in its manifest/compile/check sections. Full repo-wide CI pass is not an OCR implementation acceptance criterion until that workflow drift is fixed or explicitly scoped into a separate cleanup.

Phase 5 must still run target-scope checks for `moonshotnote-ocr` and report this repo-wide CI drift separately if it remains.

## Closure Criteria

- Every file in Package Inventory exists.
- `rg -n "moonshotnote-ocr|PP-StructureV3|canonical|low-confidence|page_type" .moonshot-relay/docs/tasks/moonshotnote-ocr-ebook-capture-ocr` returns matches.
- Phase docs include owned paths, read-only paths, dependencies, and acceptance evidence.
- Review artifact records reviewed package root, blocking findings, accepted changes, rejected/backlog changes, and remaining ambiguity.
