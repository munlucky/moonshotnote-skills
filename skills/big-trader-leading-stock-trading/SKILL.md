---
name: big-trader-leading-stock-trading
description: Use when answering Korean study questions about the book-derived 주도주/대장주 short-term trading framework, including 주도주, 대장주, 테마주 사이클, 눌림매매, 상한가 따라잡기, 돌파매매, 종가 베팅, 전상매매, 스윙매매, 비중 조절, 손절, and training-roadmap concepts. Use only public-safe summaries from the local knowledge pack, not raw OCR text.
---

# Big Trader Leading Stock Trading

This skill answers from a public-safe knowledge pack distilled from two local OCR outputs of a Korean trading book. Treat the source as third-party: do not quote or reconstruct raw source text, and do not expose private OCR files under `output/`.

## Load Order

1. Read `references/graph_manifest.json` for source boundary and counts.
2. Read `references/ontology.yaml` for node and edge types.
3. Search `references/nodes.jsonl`, `references/edges.jsonl`, and `references/chunks.jsonl` for the user's topic.
4. Use `scripts/query_knowledge.py` for keyword lookup when the topic is narrow.

## Answering Rules

- Answer in Korean unless the user asks otherwise.
- Provide study-oriented explanations, not financial advice or real-time recommendations.
- Keep claims source-grounded and mention OCR uncertainty when a detail appears noisy.
- Do not quote long passages from the source. Summarize concepts in your own words.
- If graph coverage is weak, say the local knowledge pack does not contain enough verified detail and suggest checking the private source locally.

## Useful Queries

- 주도주와 대장주의 차이는 무엇인가?
- 테마주 사이클에서 언제 조심해야 하나?
- 눌림매매와 돌파매매는 어떻게 다르게 쓰나?
- 종가 베팅에서 계좌가 무너지는 이유는 무엇인가?
- 전상매매와 상한가 따라잡기는 어떤 관계인가?
- 직장인에게 맞는 스윙매매 관점은 무엇인가?
- 월 천 프로젝트는 어떤 훈련 순서인가?

## Public Boundary

Tracked references contain summaries, normalized concept labels, relationships, keywords, and relative source refs only. Raw OCR, page text, line chunks, and page index files live under ignored `output/private-source/`.
