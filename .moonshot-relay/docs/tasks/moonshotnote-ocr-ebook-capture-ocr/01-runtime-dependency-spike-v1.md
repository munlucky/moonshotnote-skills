# Phase 1: Runtime dependency spike

Status: ready
Depends-On: none

## Goal

Decide whether PP-StructureV3 is available as an optional capability under the current skill-local install policy.

## Owned Paths

- `skills/moonshotnote-ocr/scripts/requirements.txt`
- `skills/moonshotnote-ocr/scripts/setup.ps1`
- `skills/moonshotnote-ocr/scripts/setup.sh`
- `skills/moonshotnote-ocr/scripts/doctor.py`
- `THIRD_PARTY_NOTICES.md` only if dependency/license text changes

## Read-Only Paths

- `skills/moonshotnote-ocr/scripts/ocr_image.py`
- `skills/moonshotnote-ocr/scripts/review_low_confidence.py`
- `skills/moonshotnote-ocr/SKILL.md`
- `skills/moonshotnote-ocr/agents/openai.yaml`
- `README.md`
- Generated `.venv/**`, `ocr-output/**`, model caches, review outputs

## Work

- Test `paddleocr[doc-parser]==3.4.1` first. Do not broaden to `paddleocr[all]`.
- Keep `pip install --only-binary=:all:` unless the user explicitly approves changing that install policy.
- Add a capability probe to `doctor.py` that checks import/API availability without inference or model download.
- Separate `doctor.py` output into `required_imports` and `optional_capabilities`.
- Record PP-StructureV3 as `available` or `unavailable_with_reason`.
- Define runtime metadata fields for package versions, pipeline settings, device, capability status, model source, and cache status.

## Go/No-Go

- Go: wheel-only install works, `from paddleocr import PPStructureV3` or the verified current API succeeds, and `doctor.py` reports capability without model inference.
- No-go: install/import fails, transitive dependency lacks wheels, or capability requires model download during doctor. In this case, later phases keep `pp-structure` as an explicit unavailable capability and do not route `auto` to it.

## Acceptance Evidence

- Command transcript or notes for wheel-only install spike.
- `doctor.py` JSON showing required OCR imports and optional PP-StructureV3 capability status.
- No generated runtime artifact is tracked.
- Any license/dependency notice change is reflected in `THIRD_PARTY_NOTICES.md`.

## Rollback

Revert dependency changes and leave `doctor.py` reporting `capabilities.pp_structure.available=false` with a clear reason.
