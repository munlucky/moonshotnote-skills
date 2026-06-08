#!/usr/bin/env python3
"""Build cleaned OCR outputs from moonshotnote OCR synthesis artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


STRUCTURAL_LABELS = {
    "text",
    "title",
    "number",
    "footnote",
    "header",
    "header_image",
    "footer",
    "footer_image",
    "aside_text",
    "image",
    "figure",
    "caption",
    "table",
    "formula",
}

REVIEW_STATUS_FIELDS = [
    "review_status",
    "review_note",
    "corrected_text",
    "auto_action",
    "auto_note",
    "book",
    "page_index",
    "page_type",
    "low_confidence_count",
    "chosen_source",
    "final_source",
    "quality_flags",
    "copied_image",
    "review_text_file",
    "image",
    "chosen_path",
    "new_txt",
]


@dataclass
class TextMetrics:
    score: float
    quality: str
    flags: list[str]
    unclear_count: int
    structural_label_count: int
    korean_count: int
    non_korean_cjk_count: int
    line_count: int
    char_count: int


def read_text(path: str | Path | None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return p.read_text(encoding=enc, errors="replace")
        except Exception:
            continue
    return p.read_text(errors="replace")


def split_lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]


def metric_text(text: str) -> TextMetrics:
    lines = split_lines(text)
    non_empty = [line.strip() for line in lines if line.strip()]
    char_count = len(text)
    korean_count = len(re.findall(r"[가-힣]", text))
    ascii_count = len(re.findall(r"[A-Za-z0-9]", text))
    unclear_count = text.count("[unclear]")
    replacement_count = text.count("\ufffd")
    structural_label_count = sum(1 for line in non_empty if line.lower() in STRUCTURAL_LABELS)
    non_korean_cjk_count = len(re.findall(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]", text))
    symbol_noise = len(re.findall(r"[□■◆◇▲△▼▽●○◎※]{2,}", text))

    line_count = len(non_empty)
    layout_ratio = structural_label_count / max(line_count, 1)
    korean_ratio = korean_count / max(len(re.findall(r"\S", text)), 1)
    unclear_ratio = unclear_count / max(line_count, 1)

    score = 0.0
    score += korean_count * 2.0
    score += ascii_count * 0.6
    score += min(line_count, 80) * 1.4
    score -= unclear_count * 18.0
    score -= replacement_count * 20.0
    score -= structural_label_count * 35.0
    score -= non_korean_cjk_count * 2.8
    score -= symbol_noise * 8.0
    if layout_ratio >= 0.25 and structural_label_count >= 5:
        score -= 350.0
    if unclear_ratio >= 0.35 and unclear_count >= 8:
        score -= 250.0
    if char_count < 30 and korean_count < 8 and ascii_count < 8:
        score -= 40.0
    if korean_ratio >= 0.45:
        score += 80.0

    flags: list[str] = []
    if layout_ratio >= 0.25 and structural_label_count >= 5:
        flags.append("layout-label-noise")
    if unclear_count >= 10:
        flags.append("many-unclear")
    elif unclear_count > 0:
        flags.append("has-unclear")
    if non_korean_cjk_count >= 8 and korean_count < non_korean_cjk_count:
        flags.append("non-korean-cjk-noise")
    if replacement_count:
        flags.append("replacement-char")
    if line_count == 0:
        flags.append("empty")
    if char_count < 30 and korean_count < 8 and ascii_count < 8:
        flags.append("very-short")

    if "layout-label-noise" in flags or "many-unclear" in flags or "empty" in flags:
        quality = "risky"
    elif flags:
        quality = "caution"
    else:
        quality = "ok"

    return TextMetrics(
        score=score,
        quality=quality,
        flags=flags,
        unclear_count=unclear_count,
        structural_label_count=structural_label_count,
        korean_count=korean_count,
        non_korean_cjk_count=non_korean_cjk_count,
        line_count=line_count,
        char_count=char_count,
    )


def clean_text(text: str, metrics: TextMetrics) -> str:
    lines = split_lines(text)
    cleaned: list[str] = []
    remove_structural = "layout-label-noise" in metrics.flags
    omitted_unclear = 0
    consecutive_blank = 0

    for raw in lines:
        line = raw.strip()
        lower = line.lower()
        if remove_structural and lower in STRUCTURAL_LABELS:
            continue
        if line == "[unclear]":
            omitted_unclear += 1
            continue
        if not line:
            consecutive_blank += 1
            if consecutive_blank <= 1:
                cleaned.append("")
            continue
        consecutive_blank = 0
        cleaned.append(line)

    while cleaned and not cleaned[0]:
        cleaned.pop(0)
    while cleaned and not cleaned[-1]:
        cleaned.pop()

    if omitted_unclear:
        marker = f"[unclear x{omitted_unclear} omitted]"
        if cleaned:
            cleaned.append("")
        cleaned.append(marker)

    return "\n".join(cleaned).strip()


def page_marker(page_index: int, image: str, source: str, flags: list[str], status: str) -> str:
    safe_image = Path(image).name if image else ""
    flag_text = ",".join(flags)
    return f"<!-- page:{page_index:04d} image:{safe_image} source:{source} review:{status} flags:{flag_text} -->"


def discover_compare_csvs(root: Path) -> list[Path]:
    return sorted(
        p
        for p in root.rglob("page_compare.csv")
        if "final-synthesis-v2" in str(p) and "ocr-output" in str(p)
    )


def book_from_compare_csv(csv_path: Path) -> Path:
    return csv_path.parents[2]


def choose_text(row: dict[str, str], manual_status: dict[tuple[str, str], dict[str, str]]) -> dict[str, object]:
    book = row["book"]
    page_index = row["page_index"]
    key = (book, page_index)
    manual = manual_status.get(key, {})
    corrected = (manual.get("corrected_text") or "").strip()
    status = manual.get("review_status") or ""

    chosen_text = read_text(row.get("chosen_path"))
    new_text = read_text(row.get("new_txt"))
    chosen_metrics = metric_text(chosen_text)
    new_metrics = metric_text(new_text)

    if status == "corrected" and corrected:
        final_text = corrected
        final_source = "manual-corrected"
        action = "manual-corrected"
        final_metrics = metric_text(final_text)
    elif status == "ignored":
        final_text = ""
        final_source = "manual-ignored"
        action = "manual-ignored"
        final_metrics = metric_text(final_text)
    else:
        switch_to_new = False
        if chosen_metrics.quality == "risky" and new_metrics.score > chosen_metrics.score + 40:
            switch_to_new = True
        if "layout-label-noise" in chosen_metrics.flags and "layout-label-noise" not in new_metrics.flags:
            switch_to_new = True
        if new_metrics.score > chosen_metrics.score + 160:
            switch_to_new = True

        if switch_to_new:
            final_text = new_text
            final_source = "moonshotnote-ocr-v2-paddle"
            action = "auto-switched-to-new"
            final_metrics = new_metrics
        else:
            final_text = chosen_text
            final_source = row.get("chosen_source") or "chosen"
            action = "kept-chosen"
            final_metrics = chosen_metrics

    cleaned = clean_text(final_text, final_metrics)
    cleaned_metrics = metric_text(cleaned)

    low = int(row.get("low_confidence_count") or 0)
    page_type = row.get("page_type") or ""
    flags = sorted(set(final_metrics.flags + cleaned_metrics.flags))
    needs_manual = False
    if low >= 20:
        needs_manual = True
    if page_type in {"unknown", "layout"}:
        needs_manual = True
    if "many-unclear" in flags or "layout-label-noise" in flags or "empty" in flags:
        needs_manual = True
    if final_metrics.score < -100:
        needs_manual = True

    if status in {"accepted", "corrected", "ignored", "unreadable"}:
        review_status = status
    elif needs_manual:
        review_status = "needs_manual"
    elif action == "auto-switched-to-new" or cleaned != final_text.strip():
        review_status = "corrected_auto"
    else:
        review_status = "accepted_auto"

    notes = []
    if action == "auto-switched-to-new":
        notes.append("chosen text looked worse than new OCR")
    if cleaned != final_text.strip():
        notes.append("cleaned structural labels or standalone unclear markers")
    if needs_manual:
        notes.append("manual review still recommended")
    if flags:
        notes.append("flags=" + ",".join(flags))

    return {
        "text": cleaned,
        "source": final_source,
        "status": review_status,
        "action": action,
        "note": "; ".join(notes),
        "flags": flags,
        "chosen_metrics": chosen_metrics.__dict__,
        "new_metrics": new_metrics.__dict__,
        "final_metrics": cleaned_metrics.__dict__,
    }


def load_manual_status(review_status_path: Path) -> dict[tuple[str, str], dict[str, str]]:
    if not review_status_path.exists():
        return {}
    rows: dict[tuple[str, str], dict[str, str]] = {}
    with review_status_path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows[(row.get("book") or "", row.get("page_index") or "")] = row
    return rows


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def process(root: Path) -> dict[str, object]:
    review_pack = root / "ocr-output" / "review-pack-v2"
    manual_status = load_manual_status(review_pack / "review_status.csv")
    auto_status_rows: list[dict[str, object]] = []
    collection_reports: list[dict[str, object]] = []
    all_remaining: list[dict[str, object]] = []

    for compare_csv in discover_compare_csvs(root):
        book_dir = book_from_compare_csv(compare_csv)
        book = str(book_dir.relative_to(root))
        out_dir = book_dir / "ocr-output" / "final-clean-v2"
        out_dir.mkdir(parents=True, exist_ok=True)

        page_rows: list[dict[str, str]] = []
        with compare_csv.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                row["book"] = book
                page_rows.append(row)

        md_parts: list[str] = []
        txt_parts: list[str] = []
        page_reports: list[dict[str, object]] = []
        remaining_rows: list[dict[str, object]] = []
        actions = Counter()
        statuses = Counter()
        sources = Counter()
        flags = Counter()

        for row in page_rows:
            page_index = int(row.get("page_index") or 0)
            choice = choose_text(row, manual_status)
            choice_flags = list(choice["flags"])
            text = str(choice["text"])
            marker = page_marker(page_index, row.get("image") or "", str(choice["source"]), choice_flags, str(choice["status"]))

            md_parts.append(marker)
            if text:
                md_parts.append("")
                md_parts.append(text)
            md_parts.append("")

            if text:
                txt_parts.append(text)
                txt_parts.append("")

            report = {
                **row,
                "final_source": choice["source"],
                "review_status": choice["status"],
                "auto_action": choice["action"],
                "auto_note": choice["note"],
                "quality_flags": ",".join(choice_flags),
                "final_char_count": len(text),
                "chosen_quality": choice["chosen_metrics"]["quality"],
                "new_quality": choice["new_metrics"]["quality"],
                "final_quality": choice["final_metrics"]["quality"],
                "chosen_revised_score": round(float(choice["chosen_metrics"]["score"]), 3),
                "new_revised_score": round(float(choice["new_metrics"]["score"]), 3),
                "final_revised_score": round(float(choice["final_metrics"]["score"]), 3),
            }
            page_reports.append(report)

            actions[str(choice["action"])] += 1
            statuses[str(choice["status"])] += 1
            sources[str(choice["source"])] += 1
            for flag in choice_flags:
                flags[flag] += 1

            if str(choice["status"]) == "needs_manual":
                remaining_rows.append(report)
                all_remaining.append(report)

            if (root / "ocr-output" / "review-pack-v2").exists() and (
                int(row.get("low_confidence_count") or 0) >= 10
                or (row.get("page_type") or "") in {"unknown", "layout"}
            ):
                auto_status_rows.append(
                    {
                        "review_status": choice["status"],
                        "review_note": "",
                        "corrected_text": "",
                        "auto_action": choice["action"],
                        "auto_note": choice["note"],
                        "book": book,
                        "page_index": row.get("page_index"),
                        "page_type": row.get("page_type"),
                        "low_confidence_count": row.get("low_confidence_count"),
                        "chosen_source": row.get("chosen_source"),
                        "final_source": choice["source"],
                        "quality_flags": ",".join(choice_flags),
                        "copied_image": manual_status.get((book, row.get("page_index") or ""), {}).get("copied_image", ""),
                        "review_text_file": manual_status.get((book, row.get("page_index") or ""), {}).get("review_text_file", ""),
                        "image": row.get("image"),
                        "chosen_path": row.get("chosen_path"),
                        "new_txt": row.get("new_txt"),
                    }
                )

        (out_dir / "clean_ocr.md").write_text("\n".join(md_parts).strip() + "\n", encoding="utf-8")
        (out_dir / "clean_ocr.txt").write_text("\n".join(txt_parts).strip() + "\n", encoding="utf-8")
        write_csv(
            out_dir / "postprocess_pages.csv",
            page_reports,
            [
                "page_index",
                "page_type",
                "low_confidence_count",
                "chosen_source",
                "final_source",
                "review_status",
                "auto_action",
                "quality_flags",
                "chosen_quality",
                "new_quality",
                "final_quality",
                "chosen_revised_score",
                "new_revised_score",
                "final_revised_score",
                "final_char_count",
                "image",
                "chosen_path",
                "new_txt",
                "auto_note",
            ],
        )
        write_csv(
            out_dir / "manual_review_remaining.csv",
            remaining_rows,
            [
                "page_index",
                "page_type",
                "low_confidence_count",
                "chosen_source",
                "final_source",
                "quality_flags",
                "image",
                "chosen_path",
                "new_txt",
                "auto_note",
            ],
        )

        report = {
            "book": book,
            "book_dir": str(book_dir),
            "page_count": len(page_rows),
            "outputs": {
                "clean_md": str(out_dir / "clean_ocr.md"),
                "clean_txt": str(out_dir / "clean_ocr.txt"),
                "postprocess_pages_csv": str(out_dir / "postprocess_pages.csv"),
                "manual_review_remaining_csv": str(out_dir / "manual_review_remaining.csv"),
            },
            "actions": dict(actions),
            "statuses": dict(statuses),
            "sources": dict(sources),
            "flags": dict(flags),
            "manual_remaining": len(remaining_rows),
        }
        (out_dir / "postprocess_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        collection_reports.append(report)

    collection_dir = root / "ocr-output" / "final-clean-v2"
    collection_dir.mkdir(parents=True, exist_ok=True)
    write_csv(collection_dir / "review_status.auto.csv", auto_status_rows, REVIEW_STATUS_FIELDS)
    write_csv(
        collection_dir / "manual_review_remaining.csv",
        all_remaining,
        [
            "book",
            "page_index",
            "page_type",
            "low_confidence_count",
            "chosen_source",
            "final_source",
            "quality_flags",
            "image",
            "chosen_path",
            "new_txt",
            "auto_note",
        ],
    )
    (collection_dir / "collection_postprocess_report.json").write_text(
        json.dumps(collection_reports, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    status_totals = Counter()
    action_totals = Counter()
    source_totals = Counter()
    for report in collection_reports:
        status_totals.update(report["statuses"])
        action_totals.update(report["actions"])
        source_totals.update(report["sources"])

    lines = [
        "# Ebook OCR Clean Output v2",
        "",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- root: {root}",
        f"- books: {len(collection_reports)}",
        f"- pages: {sum(r['page_count'] for r in collection_reports)}",
        f"- manual_review_remaining: {len(all_remaining)}",
        f"- statuses: {dict(status_totals)}",
        f"- actions: {dict(action_totals)}",
        f"- sources: {dict(source_totals)}",
        "",
        "## Outputs",
        "",
        f"- review_status_auto: {collection_dir / 'review_status.auto.csv'}",
        f"- manual_review_remaining: {collection_dir / 'manual_review_remaining.csv'}",
        f"- collection_report: {collection_dir / 'collection_postprocess_report.json'}",
        "",
        "## By Book",
    ]
    for report in collection_reports:
        lines.extend(
            [
                "",
                f"### {report['book']}",
                f"- pages: {report['page_count']}",
                f"- manual_review_remaining: {report['manual_remaining']}",
                f"- statuses: {report['statuses']}",
                f"- actions: {report['actions']}",
                f"- clean_md: {report['outputs']['clean_md']}",
            ]
        )
    (collection_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "collection_dir": str(collection_dir),
        "books": len(collection_reports),
        "pages": sum(r["page_count"] for r in collection_reports),
        "manual_review_remaining": len(all_remaining),
        "statuses": dict(status_totals),
        "actions": dict(action_totals),
        "sources": dict(source_totals),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="ebook collection root")
    args = parser.parse_args()
    result = process(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
