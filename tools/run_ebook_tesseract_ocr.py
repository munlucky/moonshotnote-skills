#!/usr/bin/env python3
"""Run parallel Tesseract OCR for ebook screenshot directories."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def ocr_one(image: Path, pages_dir: Path, lang: str, psm: int, force: bool) -> dict:
    out_base = pages_dir / image.stem
    out_txt = out_base.with_suffix(".txt")
    if out_txt.exists() and not force:
        text = out_txt.read_text(encoding="utf-8", errors="ignore")
        return {"image": image.name, "output": out_txt.name, "status": "cached", "chars": len(text)}
    cmd = ["tesseract", str(image), str(out_base), "-l", lang, "--psm", str(psm)]
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        return {"image": image.name, "output": out_txt.name, "status": "failed", "error": result.stderr.strip()}
    text = out_txt.read_text(encoding="utf-8", errors="ignore") if out_txt.exists() else ""
    return {"image": image.name, "output": out_txt.name, "status": "ok", "chars": len(text)}


def combine_pages(source_dir: Path, pages_dir: Path, combined_dir: Path, results: list[dict]) -> None:
    combined_dir.mkdir(parents=True, exist_ok=True)
    ok_names = {row["output"] for row in results if row["status"] in {"ok", "cached"}}
    chunks: list[str] = []
    for index, txt_path in enumerate(sorted(pages_dir.glob("*.txt")), start=1):
        if txt_path.name not in ok_names:
            continue
        text = txt_path.read_text(encoding="utf-8", errors="ignore").strip()
        chunks.append(f"# Page {index}: {txt_path.stem}\n\n{text}\n")
    combined_text = "\n\n".join(chunks).strip() + "\n"
    (combined_dir / "tesseract_all.md").write_text(combined_text, encoding="utf-8")
    plain = "\n\n".join(
        txt_path.read_text(encoding="utf-8", errors="ignore").strip()
        for txt_path in sorted(pages_dir.glob("*.txt"))
        if txt_path.name in ok_names
    ).strip() + "\n"
    (combined_dir / "tesseract_all.txt").write_text(plain, encoding="utf-8")
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_dir_name": source_dir.name,
        "engine": "tesseract",
        "lang": "kor+eng",
        "psm": 6,
        "pages_total": len(results),
        "pages_ok": sum(1 for row in results if row["status"] in {"ok", "cached"}),
        "pages_failed": sum(1 for row in results if row["status"] == "failed"),
        "combined_files": ["combined/tesseract_all.md", "combined/tesseract_all.txt"],
        "raw_source_in_repo": False,
    }
    (source_dir / "ocr-output" / "tesseract_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def process_dir(source_dir: Path, workers: int, lang: str, psm: int, force: bool) -> dict:
    images = sorted(source_dir.glob("*.png"))
    if not images:
        raise ValueError(f"{source_dir}: no PNG files")
    pages_dir = source_dir / "ocr-output" / "tesseract" / "pages"
    combined_dir = source_dir / "ocr-output" / "combined"
    pages_dir.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(ocr_one, image, pages_dir, lang, psm, force) for image in images]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    results.sort(key=lambda row: row["image"])
    combine_pages(source_dir, pages_dir, combined_dir, results)
    failed = [row for row in results if row["status"] == "failed"]
    result_path = source_dir / "ocr-output" / "tesseract_results.json"
    result_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "source": source_dir.name,
        "images": len(images),
        "ok": len(images) - len(failed),
        "failed": len(failed),
        "results": str(result_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="+")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--lang", default="kor+eng")
    parser.add_argument("--psm", type=int, default=6)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    for item in args.directories:
        summary = process_dir(Path(item), args.workers, args.lang, args.psm, args.force)
        print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
