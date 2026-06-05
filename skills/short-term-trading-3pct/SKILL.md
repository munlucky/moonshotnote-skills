---
name: short-term-trading-3pct
description: Use this local Korean study skill when the user asks about the OCR-derived concepts from "30분 투자 매일 +3% 단타 수익", including 상한가 다음날 단타, 종목 선정, HTS 세팅, 분할매수, 3% 익절, 09:30 시간 제한, and 진입 금지 패턴. This is educational analysis, not financial advice.
---

# Short-Term Trading 3 Percent Study

Use this skill to answer Korean study questions about the OCR-derived trading framework from a third-party ebook capture set. Treat all outputs as educational summaries, not investment recommendations.

## Source Boundary

- Public files contain only short, public-safe summaries and graph relationships.
- Raw OCR text from both engines is private and lives under `output/private-source/`.
- Use both source views when confidence matters:
  - `tesseract_all.md` source refs capture Tesseract `kor+eng` OCR.
  - `winrt_all.md` source refs capture WinRT Korean OCR.
- If the graph is weak or OCR noise affects a claim, say that the point is OCR-derived and needs confirmation from the image/source.

## Load Order

1. Read `references/ontology.yaml` for concept types and relationship labels.
2. Read `references/graph_manifest.json` for source quality and counts.
3. Use `references/nodes.jsonl`, `references/edges.jsonl`, and `references/chunks.jsonl` for answers.
4. For quick lookup, run `python scripts/query_knowledge.py <keyword>`.

## Answering Rules

- Answer in Korean unless the user asks otherwise.
- Prefer concise, source-grounded summaries over long quotations.
- Do not reproduce full pages, long passages, or raw OCR chunks.
- Make risk boundaries explicit: short-term trading is speculative and can lose money.
- When discussing tactics, frame them as the source's framework: "이 자료에서는..." or "OCR 지식 그래프 기준으로...".

## Useful Queries

- 상한가 다음날 종목 선정 기준은?
- HTS 세팅에서 1분봉과 8282 호가창을 왜 같이 보나?
- 진입 전 시나리오에는 무엇을 정해야 하나?
- 상한가 종가 지지선은 어떤 역할인가?
- 왜 +3% 부근에서 익절을 강조하나?
- 왜 09시30분 이후 진입을 피하나?
- 어떤 상한가 패턴은 피해야 하나?
