#!/usr/bin/env python3
"""
render_slidebook.py — Codebase Master Guide Generator

Takes a structured JSON/JS specification of slides and compiles it into a
self-contained, zero-dependency, interactive HTML slidebook with GitHub Primer
styling, high-contrast line gutters, 1:1 senior coaching notes, and quiz stations.

Usage:
    python render_slidebook.py spec.json [-o output.html]

Spec format (JSON):
{
  "projectTitle": "NFT Issuer 전수 코드 리뷰 마스터 슬라이드북",
  "slug": "nft-issuer-guide",
  "slides": [
    {
      "ch": "CH.00",
      "chTitle": "온보딩 & 인프라 아키텍처",
      "title": "[인프라 토폴로지] 5대 네트워크 망 분리",
      "sub": "클라이언트 진입점부터 DMZ, App, DB, 외부망까지의 물리적 배치",
      "type": "card",
      "contentHtml": "<div class=\"flex-1 flex flex-col justify-between space-y-4\">...</div>"
    },
    {
      "ch": "CH.03",
      "chTitle": "UserIssuanceService",
      "title": "UserIssuanceService: 2단계 광클 방지!",
      "sub": "UserIssuanceService.java:50~72",
      "lines": "UserIssuanceService.java:50~72",
      "startLine": 50,
      "highlightLines": [52, 57],
      "lang": "JAVA",
      "code": "public IssuanceResponse issueNft(...) { ... }",
      "comments": [
        { "line": "Line 52: blockingStatuses()", "text": "중복 차단 상태 반환" }
      ]
    },
    {
      "ch": "CH.12",
      "chTitle": "자가진단 퀴즈",
      "title": "퀴즈 1: 최초 202 접수 시 DB 상태는?",
      "sub": "UserIssuanceService.java:119 핵심 비즈니스 로직",
      "type": "quiz",
      "q": "O-HI 202 접수 시 우리 DB의 status는?",
      "a": "REQUESTED 상태 유지",
      "exp": "외부 202 응답은 비동기 배치 접수 완료일 뿐입니다.",
      "jumpSlideIndex": 12
    }
  ]
}
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

def validate_spec(spec):
    if not isinstance(spec, dict):
        raise ValueError("Spec must be a JSON object.")
    
    slides = spec.get("slides")
    if not isinstance(slides, list) or len(slides) == 0:
        raise ValueError("Spec must contain a non-empty 'slides' array.")

    for idx, s in enumerate(slides):
        if "title" not in s:
            raise ValueError(f"Slide {idx} is missing 'title'.")
        stype = s.get("type")
        if stype == "card":
            if not s.get("contentHtml"):
                raise ValueError(f"Card slide {idx} ({s['title']}) is missing 'contentHtml'.")
        elif stype == "quiz":
            if not s.get("q") or not s.get("a") or not s.get("exp"):
                raise ValueError(f"Quiz slide {idx} ({s['title']}) requires 'q', 'a', and 'exp'.")
        else:
            # Code slide
            if not s.get("code"):
                raise ValueError(f"Code slide {idx} ({s['title']}) is missing 'code'.")

def render(spec_path, output_path=None):
    spec_file = Path(spec_path).resolve()
    if not spec_file.exists():
        print(f"Error: Spec file not found: {spec_file}", file=sys.stderr)
        sys.exit(1)

    with open(spec_file, "r", encoding="utf-8") as f:
        spec = json.load(f)

    validate_spec(spec)

    script_dir = Path(__file__).parent.resolve()
    template_file = script_dir.parent / "templates" / "slidebook-template.html"
    if not template_file.exists():
        print(f"Error: Template not found at {template_file}", file=sys.stderr)
        sys.exit(1)

    with open(template_file, "r", encoding="utf-8") as f:
        template = f.read()

    project_title = spec.get("projectTitle", "코드베이스 전수 리뷰 마스터 슬라이드북")
    slides = spec.get("slides", [])
    total_slides = len(slides)
    slides_json_str = json.dumps(slides, ensure_ascii=False, indent=2)

    # Replace placeholders
    html_out = template.replace("{{PROJECT_TITLE}}", project_title)
    html_out = html_out.replace("{{TOTAL_SLIDES}}", str(total_slides))
    html_out = html_out.replace("{{SLIDES_JSON}}", slides_json_str)

    if not output_path:
        slug = spec.get("slug", "codebase-guide")
        today = datetime.date.today().strftime("%Y-%m-%d")
        output_path = spec_file.parent / f"{today}-{slug}.html"
    else:
        output_path = Path(output_path).resolve()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"Successfully rendered {total_slides} slides to:")
    print(f"  -> {output_path} (Size: {len(html_out):,} bytes)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render interactive slidebook from spec JSON.")
    parser.add_argument("spec", help="Path to input spec.json")
    parser.add_argument("-o", "--output", help="Optional output HTML path")
    args = parser.parse_args()

    render(args.spec, args.output)
