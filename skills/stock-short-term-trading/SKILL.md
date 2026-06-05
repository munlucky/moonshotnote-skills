---
name: stock-short-term-trading
description: Korean short-term stock trading knowledge pack built from two OCR outputs of a trading book. Use when Codex needs public-safe summaries or study guidance about Korean 단타/스윙 trading concepts, risk control, trader mindset, HTS/MTS setup, moving averages, order book, volume, theme stocks, closing-price bets, after-hours single-price trading, NXT/KRX differences, or worker-friendly trading routines. Do not use it to reproduce the source text.
---

# Stock Short Term Trading

## Overview

Use this skill to answer Korean short-term stock trading study questions from a public-safe knowledge graph. The private OCR source is excluded from the skill surface; answer from summaries and source refs, not from raw copied passages.

## Source Boundary

- Treat the source as `third-party`.
- Do not quote or reconstruct long passages from the OCR text.
- Use `references/chunks.jsonl` for topic summaries and `references/nodes.jsonl` / `references/edges.jsonl` for concept relationships.
- Cite source refs as page or OCR-source ranges when helpful.
- When OCR quality is weak or graph coverage is thin, say so and answer at concept level.

## Quick Workflow

1. Read `references/graph_manifest.json` to understand scope and source quality.
2. Search `references/chunks.jsonl` with keywords from the user request.
3. Load matching nodes from `references/nodes.jsonl` and supporting relationships from `references/edges.jsonl`.
4. Answer in Korean with practical caveats: this is study material, not investment advice.
5. If the user asks for exact text, explain that the skill only exposes public-safe summaries.

## Helpful Script

Run this from the skill directory for quick local lookup:

```powershell
py -3 scripts/query_knowledge.py --query "호가창 거래량"
```

The script returns matching public-safe chunks, nodes, and relationships.
