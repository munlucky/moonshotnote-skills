from __future__ import annotations

from pathlib import Path
from typing import Any

from ocr_pipeline.classifiers.page_type import PAGE_TYPES, PageTypeResult, classify_page_type
from ocr_pipeline.engines.paddle import PaddleRunner, run_paddle
from ocr_pipeline.engines.pp_structure import pp_structure_available, probe_pp_structure, run_pp_structure
from ocr_pipeline.engines.surya import run_surya, surya_available
from ocr_pipeline.models import OcrResult
from ocr_pipeline.postprocess.columns import restore_columns
from ocr_pipeline.postprocess.paragraphs import restore_paragraphs


ENGINES = {"auto", "paddle", "pp-structure", "surya"}


def run_ocr(
    image_path: Path,
    *,
    engine: str,
    page_mode: str,
    lang: str,
    out_dir: Path,
    paddle_runner: PaddleRunner | None = None,
) -> OcrResult:
    if engine not in ENGINES:
        raise ValueError(f"Unsupported engine: {engine}")
    if page_mode not in PAGE_TYPES:
        raise ValueError(f"Unsupported page mode: {page_mode}")

    if engine == "paddle":
        result = run_paddle(image_path, lang, paddle_runner)
        return finalize(result, requested_engine=engine, page_mode=page_mode)
    if engine == "surya":
        result = run_surya(image_path, out_dir)
        return finalize(result, requested_engine=engine, page_mode=page_mode)
    if engine == "pp-structure":
        result = run_pp_structure(image_path)
        return finalize(result, requested_engine=engine, page_mode=page_mode)

    return run_auto(image_path, page_mode=page_mode, lang=lang, out_dir=out_dir, paddle_runner=paddle_runner)


def run_auto(
    image_path: Path,
    *,
    page_mode: str,
    lang: str,
    out_dir: Path,
    paddle_runner: PaddleRunner | None,
) -> OcrResult:
    try:
        paddle_result = run_paddle(image_path, lang, paddle_runner)
    except Exception as paddle_error:
        if surya_available():
            result = run_surya(image_path, out_dir)
            result.fallback_used = True
            result.fallback_reason = f"paddle_error: {paddle_error}"
            result.warnings.append(f"PaddleOCR fallback reason: {paddle_error}")
            return finalize(result, requested_engine="auto", page_mode="unknown")
        raise

    if not paddle_result.text.strip():
        if surya_available():
            result = run_surya(image_path, out_dir)
            result.fallback_used = True
            result.fallback_reason = "paddle_empty_text"
            return finalize(result, requested_engine="auto", page_mode="unknown")
        paddle_result.warnings.append("PaddleOCR produced empty text and Surya is unavailable.")
        return finalize(paddle_result, requested_engine="auto", page_mode="unknown")

    page_type = classify_or_override(paddle_result, page_mode)
    apply_page_type(paddle_result, page_type)

    if page_type.page_type == "table":
        if pp_structure_available():
            try:
                result = run_pp_structure(image_path)
                result.fallback_used = True
                result.fallback_reason = "page_type=table"
                return finalize(result, requested_engine="auto", page_mode=page_type.page_type)
            except Exception as exc:
                paddle_result.warnings.append(f"PP-StructureV3 fallback failed; keeping PaddleOCR result: {exc}")
                paddle_result.fallback_reason = "pp_structure_failed"
        else:
            paddle_result.warnings.append(f"PP-StructureV3 unavailable: {probe_pp_structure()['reason']}")
            paddle_result.fallback_reason = "pp_structure_unavailable"

    if page_type.page_type in {"multi-column", "layout"}:
        if surya_available():
            try:
                result = run_surya(image_path, out_dir)
                result.fallback_used = True
                result.fallback_reason = f"page_type={page_type.page_type}"
                return finalize(result, requested_engine="auto", page_mode=page_type.page_type)
            except Exception as exc:
                paddle_result.warnings.append(f"Surya fallback failed; keeping PaddleOCR result: {exc}")
                paddle_result.fallback_reason = "surya_failed"
        else:
            paddle_result.warnings.append("Surya fallback unavailable; keeping PaddleOCR result.")
            paddle_result.fallback_reason = "surya_unavailable"

    return finalize(paddle_result, requested_engine="auto", page_mode=page_type.page_type)


def finalize(result: OcrResult, *, requested_engine: str, page_mode: str) -> OcrResult:
    result.requested_engine = requested_engine
    if result.page_type == "unknown":
        page_type = classify_or_override(result, page_mode)
        apply_page_type(result, page_type)
    if result.page_type == "plain-text":
        result.structured["paragraphs"] = restore_paragraphs(result.items)
    elif result.page_type in {"multi-column", "layout"}:
        result.structured["columns"] = restore_columns(result.items)
    result.runtime_metadata.setdefault("capabilities", {})
    result.runtime_metadata["capabilities"].setdefault("pp_structure", probe_pp_structure())
    result.runtime_metadata["capabilities"].setdefault("surya", {"available": surya_available()})
    return result


def classify_or_override(result: OcrResult, page_mode: str) -> PageTypeResult:
    if page_mode != "auto":
        return PageTypeResult(page_mode, 1.0, {"override": 1.0})
    return classify_page_type(result.items)


def apply_page_type(result: OcrResult, page_type: PageTypeResult) -> None:
    result.page_type = page_type.page_type
    result.page_type_confidence = page_type.confidence
    result.page_type_scores = page_type.scores
