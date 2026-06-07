# Phase 4: Docs and review workflow

Status: ready
Depends-On: Phase 3

## Goal

Update user-facing skill instructions and keep low-confidence visual review compatible with the canonical schema.

## Owned Paths

- `skills/moonshotnote-ocr/SKILL.md`
- `skills/moonshotnote-ocr/agents/openai.yaml`
- `README.md`
- `skills/moonshotnote-ocr/scripts/review_low_confidence.py` only if canonical schema requires compatibility handling
- `.github/workflows/validate.yml` only for target-scope `moonshotnote-ocr` compile/manifest path updates
- `THIRD_PARTY_NOTICES.md` only if Phase 1 changed dependency/license scope

## Read-Only Paths

- `skills/moonshotnote-ocr/scripts/ocr_pipeline/**` except docs-driven typo fixes
- `skills/moonshotnote-ocr/scripts/setup.ps1`
- `skills/moonshotnote-ocr/scripts/setup.sh`
- Generated review outputs/contact sheets/manifests
- Unrelated skill docs

## Work

- Update `SKILL.md` to describe Paddle-first, page-type routing, PP-Structure optional capability, and Surya optional fallback.
- Preserve low-confidence closeout policy: do not imply OCR is final while `needs_review` remains.
- Update `agents/openai.yaml` default prompt to mention structured ebook capture OCR only if concise.
- Update root `README.md`; do not assume a skill-local README exists.
- Document that `--engine paddle` avoids Surya runtime use.
- Document that PP-StructureV3 may be unavailable and how `doctor.py` reports that state.
- If `review_low_confidence.py` changes, keep its current input contract: JSON file or directory, `payload.input`, `items[].text/confidence/box`.

## Acceptance Evidence

- `SKILL.md` still has valid frontmatter and concise trigger text.
- `agents/openai.yaml` matches the revised skill behavior.
- README usage examples include `--page-mode auto`, explicit Paddle-only mode, and low-confidence review.
- Surya GPL/runtime note remains present.
- No generated review output is tracked.

## Backlog

- Removing `opencv-python`.
- Adding viewer UI crop/body crop preprocessing.
- VLM/Tesseract routes.
- Global skill install sync, commit, and push.
