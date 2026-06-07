# Phase 5: Verification closeout

Status: ready
Depends-On: Phase 4

## Goal

Verify the OCR skill changes with target-scope static, contract, and local runtime evidence while keeping repo-wide CI drift separate.

## Owned Paths

- `skills/moonshotnote-ocr/tests/**`
- `skills/moonshotnote-ocr/scripts/ocr_pipeline/**` only for fixes required by failed tests
- `skills/moonshotnote-ocr/scripts/ocr_image.py` only for fixes required by failed tests
- Plan package review/verification notes if execution updates are recorded

## Read-Only Paths

- Generated `.venv/**`, `ocr-output/**`, `low-confidence-review/**`, model caches
- Unrelated skill folders
- `C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py`

## Required Static Checks

```powershell
$env:PYTHONUTF8 = "1"
py -3 -m py_compile skills\moonshotnote-ocr\scripts\ocr_image.py
py -3 -m py_compile (Get-ChildItem skills\moonshotnote-ocr\scripts\ocr_pipeline -Recurse -Filter *.py).FullName
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\moonshotnote-ocr
npx -y skills add . --skill moonshotnote-ocr --list
```

Repo-wide `npx -y skills add . --list` is optional because current workflow/docs may still reference removed trading skills.

## Required Contract Tests

- Existing Paddle JSON keeps `engine/input/text/items/warnings/low_confidence`.
- Existing Surya JSON keeps `engine/input/text/items/warnings/low_confidence`.
- Existing `auto` empty/fail fallback behavior remains covered.
- New fields are present for new paths and absent/optional in a backward-compatible way for old fixtures.
- `review_low_confidence.py` produces crops/contact sheets/manifest from canonical JSON.

## Local OCR Smoke

Run only when the skill-local OCR runtime is installed and model download/cache conditions are acceptable.

- Plain text fixture: `--engine paddle --page-mode auto`; no fallback expected.
- Table fixture: `--engine auto --page-mode auto`; PP-Structure result or explicit unavailable warning expected.
- Multi-column/layout fixture: Surya result or explicit unavailable warning expected.
- Low-confidence fixture: review manifest contains correct status counts and no `needs_review` closeout claim is made.

## Closeout Report

Report:

- commands run and pass/fail status
- outputs written
- optional capability states
- fallback behavior observed
- generated artifacts excluded from tracked package payload
- unresolved repo-wide CI drift, if `.github/workflows/validate.yml` still references removed skill paths

## Completion Rule

The OCR plan can complete with PP-StructureV3 unavailable only if:

- Phase 1 records the unavailable reason,
- `--engine pp-structure` fails clearly,
- `auto` keeps Paddle output with warning instead of silent failure,
- all Paddle/Surya compatibility tests pass.
