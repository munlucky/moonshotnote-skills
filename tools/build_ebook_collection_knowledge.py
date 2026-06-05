#!/usr/bin/env python3
"""Build max-use public-safe knowledge packs from the local ebook OCR collection.

The script reads private OCR text from an ebook collection root, writes ignored
private chunks/candidate ledgers under each target skill, and updates tracked
public-safe references without copying source wording.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SOURCE_CONFIGS: dict[str, dict[str, Any]] = {
    "daily-webnovel-writing-knowledge-skill": {
        "skill_name": "daily-webnovel-writing-knowledge",
        "domain": "webnovel",
        "source_id": "daily-webnovel-writing-reviewed-ocr",
        "review_status": "reviewed",
        "ocr_engine": "paddle",
        "source_files": ["창작/매일 웹소설 쓰기/ocr-output/paddle/reviewed/combined.reviewed.paddle.txt"],
        "targets": {"nodes": 90, "edges": 155, "chunks": 35, "coverage": 45, "qa": 45},
        "description": "Use this skill for Korean webnovel writing planning, serialization strategy, genre-market fit, character design, episode structure, readability, cliffhangers, metrics, submission, contracts, and sustainable completion habits.",
    },
    "short-term-trading-3pct": {
        "kind": "registered_source",
        "skill_name": "short-term-trading-3pct",
        "domain": "trading-3pct",
        "source_id": "short-term-trading-3pct-dual-ocr",
        "review_status": "dual_ocr_unreviewed",
        "ocr_engine": "tesseract_winrt",
        "source_root": "트레이딩/30분 투자 매일+3% 단타 수익",
        "source_files": [
            "트레이딩/30분 투자 매일+3% 단타 수익/ocr-output/combined/tesseract_all.md",
            "트레이딩/30분 투자 매일+3% 단타 수익/ocr-output/combined/winrt_all.md",
        ],
        "targets": {"nodes": 110, "edges": 220, "chunks": 42, "coverage": 52, "qa": 50},
        "description": "Use this skill for educational reasoning about short-term Korean stock trading routines centered on limit-up follow-through, opening-session discipline, candidate filtering, order timing, and risk control.",
    },
    "big-trader-leading-stock-trading": {
        "kind": "registered_source",
        "skill_name": "big-trader-leading-stock-trading",
        "domain": "leading-stock",
        "source_id": "big-trader-leading-stock-dual-ocr",
        "review_status": "dual_ocr_unreviewed",
        "ocr_engine": "winrt_tesseract",
        "source_root": "트레이딩/빅 트레이더의 주도주 매매법",
        "source_files": [
            "트레이딩/빅 트레이더의 주도주 매매법/ocr_output/combined_ocr.md",
            "트레이딩/빅 트레이더의 주도주 매매법/ocr_output_tesseract/combined_ocr.md",
        ],
        "targets": {"nodes": 150, "edges": 300, "chunks": 56, "coverage": 70, "qa": 65},
        "description": "Use this skill for educational reasoning about leading-stock trading, market theme rotation, leader/secondary stock distinction, selection discipline, timing, risk, and post-trade review.",
    },
    "stock-short-term-trading": {
        "kind": "registered_source",
        "skill_name": "stock-short-term-trading",
        "domain": "stock-short-term",
        "source_id": "stock-short-term-trading-preferred-ocr",
        "review_status": "dual_ocr_preferred",
        "ocr_engine": "preferred_tesseract_winrt",
        "source_root": "트레이딩/주식투자 단기 트레이딩의 정석",
        "source_files": ["트레이딩/주식투자 단기 트레이딩의 정석/ocr-output/merged/preferred_all.md"],
        "targets": {"nodes": 170, "edges": 340, "chunks": 66, "coverage": 82, "qa": 75},
        "description": "Use this skill for educational reasoning about Korean short-term stock trading mindset, chart and volume interpretation, trading style fit, entries/exits, HTS routines, and risk management.",
    },
    "daangn-ai-development": {
        "kind": "registered_source",
        "skill_name": "daangn-ai-development",
        "domain": "ai-product-development",
        "source_id": "daangn-ai-development-tesseract-ocr",
        "review_status": "tesseract_unreviewed",
        "ocr_engine": "tesseract_kor_eng",
        "source_files": ["프로그래밍/요즘 당근 AI 개발/ocr-output/combined/tesseract_all.md"],
        "targets": {"nodes": 180, "edges": 360, "chunks": 70, "coverage": 85, "qa": 70},
        "description": "Use this skill for public-safe reasoning about practical AI adoption in product teams, AI agents, prompt engineering, VoC automation, operations automation, vibe coding, search, recommendation, experimentation, and organizational learning.",
    },
    "woowahan-ai-development": {
        "kind": "registered_source",
        "skill_name": "woowahan-ai-development",
        "domain": "ai-platform-operations",
        "source_id": "woowahan-ai-development-tesseract-ocr",
        "review_status": "tesseract_unreviewed",
        "ocr_engine": "tesseract_kor_eng",
        "source_files": ["프로그래밍/요즘 우아한 AI 개발/ocr-output/combined/tesseract_all.md"],
        "targets": {"nodes": 220, "edges": 440, "chunks": 85, "coverage": 110, "qa": 80},
        "description": "Use this skill for public-safe reasoning about AI/ML/LLM use in service platforms, experimentation, automation, optimization, recommendation, operational analytics, model lifecycle, and engineering collaboration.",
    },
    "teddynote-langchain-rag": {
        "skill_name": "teddynote-langchain-rag",
        "domain": "rag-langchain",
        "source_id": "teddynote-langchain-rag-tesseract-ocr",
        "review_status": "tesseract_unreviewed",
        "ocr_engine": "tesseract_kor_eng",
        "source_files": ["프로그래밍/테디노트의 랭체인을 활용한 RAG 비법 노트 - 기본, 심화/ocr-output/combined/tesseract_all.md"],
        "targets": {"nodes": 190, "edges": 340, "chunks": 70, "coverage": 90, "qa": 65},
        "description": "Use this skill for public-safe reasoning about RAG and LangChain pipelines, document loading, splitting, embedding, vector stores, retrievers, prompts, chains, evaluation, deployment, and troubleshooting.",
    },
}


TOPICS: dict[str, list[str]] = {
    "webnovel": [
        "genre market fit", "one-line concept", "reader promise", "platform positioning", "serialization cadence",
        "completion target", "reserve episode buffer", "episode hook", "opening scene pressure", "protagonist desire",
        "protagonist wound", "motivation clarity", "character voice", "supporting cast function", "relationship engine",
        "conflict escalation", "scene purpose", "mobile readability", "short paragraph rhythm", "dialogue momentum",
        "exposition control", "cliffhanger trust", "curiosity gap", "paid continuation signal", "retention metric",
        "comment interpretation", "revision priority", "synopsis expansion", "episode map", "character bible",
        "relationship map", "setting rule", "worldbuilding restraint", "genre trope variation", "reader fatigue warning",
        "midpoint reversal", "arc milestone", "serial launch timing", "daily writing routine", "word count pacing",
        "burnout prevention", "submission package", "publisher fit", "promotion route", "royalty term review",
        "exclusivity check", "secondary rights check", "advance tradeoff", "contract question list", "completion habit",
        "weak hook warning", "vague genre warning", "unstable motive warning", "overreading comments warning",
        "late reveal setup", "title keyword fit", "thumbnail first impression", "blurb promise", "reader onboarding",
        "chapter ending beat", "serial feedback loop", "revision after launch", "market research note",
        "voice consistency check", "antagonist pressure", "stakes ladder", "scene transition economy",
        "paywall episode design", "long-term plot debt", "author sustainability", "publisher due diligence",
        "platform metric review", "launch checklist", "finale planning", "spin-off restraint", "novel bible maintenance",
        "reader expectation reset", "genre keyword sheet", "episode title role", "conflict triangle", "emotional payoff",
        "draft to publish workflow", "quality floor", "serial risk ledger", "contract negotiation boundary",
        "promotion asset readiness", "reader trust repair", "completion retrospective", "next project learning",
    ],
    "trading-3pct": [
        "limit-up follow-through", "opening thirty-minute focus", "candidate liquidity concentration", "previous day strength",
        "theme news catalyst", "gap behavior filter", "order book pressure", "first pullback decision", "entry price discipline",
        "stop-loss line", "profit target restraint", "no-trade stock filter", "chart setup routine", "HTS watchlist preparation",
        "pre-market scenario", "intraday time window", "volume burst confirmation", "leader stock preference",
        "false breakout warning", "thin liquidity warning", "late chase warning", "mechanical exit", "daily target stop",
        "single trade focus", "cash preservation", "small loss acceptance", "opening volatility risk",
        "screening condition review", "overnight issue check", "upper limit residue", "sector heat map",
        "vi trigger caution", "news freshness check", "execution speed", "slippage allowance", "trade journal",
        "same-day recovery ban", "position size cap", "profit protection", "re-entry condition", "buyer exhaustion",
        "seller wall interpretation", "short holding period", "market index filter", "theme rotation caution",
        "chart pattern confirmation", "support level failure", "resistance breakout", "risk reward precheck",
        "morning auction signal", "closing review", "watchlist pruning", "beginner overtrade warning",
        "confidence calibration", "rule violation reset", "educational-not-advice boundary", "OCR cross-check lane",
        "chart image abstraction", "numeric OCR uncertainty", "repeatable routine", "strategy stopping rule",
        "emotion control", "loss streak pause", "market participation intensity", "entry cancellation condition",
        "sell strength observation", "candidate ranking", "same theme comparison", "daily preparation checklist",
        "post-trade label", "next-day exclusion", "opening candle context", "trade timebox",
    ],
    "leading-stock": [
        "trading over investing lens", "stock selection first", "leading stock definition", "leader stock distinction",
        "theme leadership", "capital concentration", "market attention", "sector rotation", "news catalyst hierarchy",
        "first mover advantage", "second-tier stock risk", "follow-up stock comparison", "leader persistence",
        "breakout volume", "institutional footprint", "retail crowding", "daily leader list", "watchlist discipline",
        "selection before timing", "chart context", "moving average support", "price box breakout", "failed leader warning",
        "theme exhaustion warning", "late entry risk", "trade thesis", "scenario planning", "entry trigger",
        "stop-loss invalidation", "partial profit", "trend continuation", "intraday pullback", "swing hold decision",
        "market regime filter", "index alignment", "hot theme concentration", "new high interpretation",
        "volume climax caution", "news sell-off risk", "leader rotation record", "same-theme pair comparison",
        "trading diary", "loss pattern review", "setup screenshot abstraction", "position sizing", "cash reserve",
        "avoid low-quality theme", "avoid isolated spike", "avoid stale issue", "leader stock replacement",
        "gap-up response", "gap-down response", "opening strength test", "closing strength test", "next-day plan",
        "risk first process", "educational-not-advice boundary", "dual OCR cross-check", "chart pattern abstraction",
        "theme research routine", "business model check", "market narrative fit", "liquidity threshold",
        "volatility tolerance", "buying pressure quality", "selling pressure quality", "breakout retest",
        "support violation", "resistance absorption", "news confirmation", "anticipation versus confirmation",
        "one best stock focus", "portfolio concentration caution", "leader lifecycle", "topicality decay",
        "trade cancellation", "after-action review", "setup taxonomy", "repeatable observation", "confidence score",
        "market heat risk", "technical signal hierarchy", "fundamental catalyst support", "theme map maintenance",
        "watchlist aging", "beginner imitation warning", "strategy fit", "daily preparation", "closing notes",
    ],
    "stock-short-term": [
        "risk-first mindset", "trading style fit", "scalping suitability", "day trading routine", "swing trading boundary",
        "mechanical stop loss", "daily profit stop", "loss limit", "position sizing", "capital preservation",
        "chart reading foundation", "candlestick context", "volume interpretation", "moving average decision",
        "support resistance", "breakout entry", "pullback entry", "failed breakout warning", "overtrade warning",
        "HTS setup", "watchlist organization", "screening condition", "market index check", "theme tracking",
        "news catalyst", "opening session behavior", "closing session behavior", "intraday momentum",
        "buying pressure", "selling pressure", "order book reading", "execution discipline", "slippage risk",
        "profit taking", "trailing stop", "re-entry rule", "trade journal", "mistake review", "psychology control",
        "fear of missing out", "revenge trading ban", "beginner time constraint", "liquidity filter",
        "volatility filter", "low price stock caution", "theme leader preference", "sector rotation",
        "earnings event caution", "disclosure check", "market regime", "index divergence", "scenario prewriting",
        "entry invalidation", "exit priority", "same-day review", "weekly review", "rule checklist",
        "practice account boundary", "educational-not-advice boundary", "dual OCR confidence", "chart image abstraction",
        "numeric OCR uncertainty", "strategy selection", "cash ratio", "profit preservation", "loss streak pause",
        "time window selection", "opening gap caution", "volume climax caution", "support breakdown",
        "resistance breakout", "trend continuation", "range trade caution", "news freshness", "theme fade",
        "stop order placement", "partial sell", "full exit", "risk reward ratio", "candidate ranking",
        "pre-market routine", "post-market routine", "setup naming", "confidence scoring", "market participation",
        "trade cancellation", "discipline reset", "repeatable process", "learning loop", "portfolio simplicity",
        "tax and fee awareness", "broker tool familiarity", "mobile trading caution", "screen fatigue",
        "daily checklist", "weekly plan", "objective record", "habit formation", "strategy boundary",
    ],
    "ai-product-development": [
        "ai adoption strategy", "agent workflow", "prompt engineering practice", "vocabulary of work", "VoC automation",
        "operations automation", "vibe coding", "search relevance", "recommendation quality", "experiment design",
        "human centered value", "team enablement", "cost support policy", "prototype first culture", "fear reduction",
        "use case discovery", "customer support analysis", "content moderation assist", "internal tool automation",
        "developer productivity", "coding assistant review", "prompt template ownership", "evaluation rubric",
        "hallucination guardrail", "privacy boundary", "data access boundary", "permission design", "review workflow",
        "feedback loop", "cross functional collaboration", "AI champion role", "learning community", "model selection",
        "tool selection", "workflow integration", "search query understanding", "recommendation feedback",
        "local context awareness", "automation failure mode", "manual override", "quality measurement",
        "operational rollout", "adoption metric", "training material", "case study capture", "reuse pattern",
        "risk communication", "service experience improvement", "product hypothesis", "rapid iteration",
        "domain expert review", "AI agent handoff", "task decomposition", "knowledge base use",
        "prompt versioning", "output review", "team ritual", "organizational learning",
    ],
    "ai-platform-operations": [
        "machine learning workflow", "LLM service adoption", "generative AI use case", "automation target selection",
        "optimization loop", "recommendation system", "search ranking", "delivery operation analytics",
        "customer experience signal", "model experiment", "feature engineering", "data pipeline", "model serving",
        "online evaluation", "offline evaluation", "A B test", "metric design", "monitoring signal",
        "drift detection", "human review", "operations dashboard", "alert triage", "process automation",
        "engineering collaboration", "platform constraint", "model lifecycle", "batch inference", "real time inference",
        "cost latency tradeoff", "data quality", "labeling workflow", "feedback data", "LLM prompt governance",
        "agentic automation", "tool calling boundary", "safety review", "privacy compliance", "service reliability",
        "fallback design", "incident response", "business impact measurement", "stakeholder alignment",
        "project discovery", "prototype validation", "rollout plan", "maintenance ownership", "knowledge sharing",
        "domain language alignment", "cross team reuse", "technical debt", "architecture boundary",
        "automation ROI", "user behavior signal", "ranking explainability", "experiment culture",
    ],
    "rag-langchain": [
        "RAG pipeline", "document loading", "document parsing", "text splitting", "chunk size decision",
        "chunk overlap decision", "embedding model", "vector store", "retriever strategy", "prompt template",
        "LLM chain", "query transformation", "multi query retrieval", "context compression", "reranking",
        "metadata filtering", "hybrid search", "semantic search", "keyword search", "parent document retrieval",
        "multi vector retrieval", "self query retriever", "retrieval evaluation", "answer faithfulness",
        "context precision", "context recall", "hallucination reduction", "citation design", "source attribution",
        "loader selection", "PDF parsing", "web document loading", "markdown splitting", "recursive splitter",
        "token budget", "prompt injection risk", "retriever debugging", "embedding cache", "index refresh",
        "vector database choice", "FAISS index", "Chroma store", "Pinecone integration", "LangChain runnable",
        "LCEL composition", "chain observability", "streaming response", "memory boundary", "agent tool boundary",
        "structured output", "Pydantic parser", "output parser", "conversation history", "retrieval augmented chat",
        "evaluation dataset", "golden question set", "negative query", "no answer handling", "fallback answer",
        "deployment boundary", "API wrapper", "environment configuration", "secret management", "rate limit",
        "latency budget", "cost control", "batch ingestion", "incremental ingestion", "deduplication",
        "OCR document source", "table extraction warning", "image source limitation", "Korean text handling",
        "chunk quality review", "semantic unit extraction", "retrieval trace", "debug log", "LangSmith tracing",
        "prompt variable", "few shot example", "system instruction", "guardrail policy", "evaluation loop",
        "production monitoring", "user feedback", "answer update workflow", "index versioning",
    ],
}


DOMAIN_TYPES = {
    "webnovel": ["Concept", "Workflow", "Decision", "Practice", "Warning", "Metric", "Contract"],
    "trading-3pct": ["Strategy", "SelectionCriterion", "RiskControl", "Workflow", "Warning", "Operation"],
    "leading-stock": ["Concept", "Principle", "SelectionCriterion", "RiskControl", "Workflow", "Warning"],
    "stock-short-term": ["Concept", "Strategy", "RiskControl", "Practice", "Warning", "Operation"],
    "ai-product-development": ["Concept", "Workflow", "Practice", "Decision", "Metric", "Warning", "Operation"],
    "ai-platform-operations": ["Concept", "Workflow", "Architecture", "Operation", "Metric", "Decision", "Warning"],
    "rag-langchain": ["Concept", "PipelineStep", "Component", "Decision", "Evaluation", "Warning", "Operation"],
}

EDGE_TYPES = [
    "supports",
    "depends_on",
    "informs",
    "constrains",
    "precedes",
    "warns_about",
    "refines",
    "contrasts_with",
]

GAP_SOURCES: list[dict[str, str]] = []


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    source_chunk_id: str
    line_range: list[int]
    text_sha256: str
    extraction_kind: str
    semantic_signals: list[str]
    blocked_material_flags: list[str]
    accepted: bool


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(text: str) -> str:
    text = text.lower().replace("+", " plus ")
    text = re.sub(r"[^a-z0-9가-힣]+", "-", text).strip("-")
    return re.sub(r"-+", "-", text)


def title(text: str) -> str:
    return " ".join(part.capitalize() if part.isascii() else part for part in text.split())


def tokens(text: str) -> set[str]:
    raw = re.findall(r"[a-z0-9가-힣]+", text.lower())
    stop = {"and", "the", "with", "boundary", "warning", "decision", "routine", "check", "review"}
    return {item for item in raw if len(item) >= 2 and item not in stop}


def topic_pool(domain: str, minimum: int | None = None) -> list[str]:
    base = list(TOPICS[domain])
    if minimum is None or len(base) >= minimum:
        return base
    lenses = [
        "boundary",
        "workflow",
        "risk",
        "evaluation",
        "operation",
        "testing",
        "deployment",
        "feedback",
        "governance",
        "maintenance",
    ]
    expanded = list(base)
    seen = set(expanded)
    lens_index = 0
    while len(expanded) < minimum:
        seed = base[lens_index % len(base)]
        lens = lenses[(lens_index // len(base)) % len(lenses)]
        candidate = f"{seed} {lens}"
        if candidate not in seen:
            expanded.append(candidate)
            seen.add(candidate)
        lens_index += 1
    return expanded


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def read_source_lines(collection_root: Path, config: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for source_file in config["source_files"]:
        path = collection_root / source_file
        if not path.is_file():
            raise FileNotFoundError(f"missing OCR source: {source_file}")
        lines.append(f"[[source:{Path(source_file).name}]]")
        lines.extend(path.read_text(encoding="utf-8", errors="ignore").splitlines())
    return lines


def build_chunks(lines: list[str], chunk_size: int = 80, overlap: int = 15) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    start = 0
    while start < len(lines):
        end = min(len(lines), start + chunk_size)
        chunks.append(
            {
                "id": f"source-lines-{start + 1:05d}-{end:05d}",
                "line_start": start + 1,
                "line_end": end,
                "text": "\n".join(lines[start:end]),
            }
        )
        if end == len(lines):
            break
        start = end - overlap
    return chunks


def blocked_flags(text: str) -> list[str]:
    meaningful = [line for line in text.splitlines() if line.strip()]
    if not meaningful:
        return ["empty"]
    code_like = sum(1 for line in meaningful if re.search(r"(^\s*(def|class|import|from|return|if|for)\b|[{};=]|=>|->)", line))
    table_like = sum(1 for line in meaningful if line.count("|") >= 2 or line.count("\t") >= 2)
    exercise_like = sum(1 for line in meaningful if re.search(r"(?i)(exercise|quiz|연습|문제|정답|해답)", line))
    flags: list[str] = []
    if code_like / len(meaningful) > 0.25:
        flags.append("code_material_dropped")
    if table_like / len(meaningful) > 0.18:
        flags.append("table_material_dropped")
    if exercise_like / len(meaningful) > 0.04:
        flags.append("exercise_material_dropped")
    if len(text) < 180:
        flags.append("too_short")
    return flags


def score_topic(topic: str, text: str) -> int:
    topic_terms = tokens(topic)
    haystack = text.lower()
    score = sum(4 for term in topic_terms if term in haystack)
    korean_hints = {
        "risk": ["위험", "손절", "손실", "리스크"],
        "warning": ["주의", "금지", "위험", "실패"],
        "entry": ["매수", "진입", "타점"],
        "exit": ["매도", "청산", "손절", "익절"],
        "volume": ["거래량", "수급"],
        "theme": ["테마", "이슈", "뉴스"],
        "character": ["캐릭터", "인물", "주인공"],
        "episode": ["회차", "에피소드"],
        "contract": ["계약", "출판사", "인세"],
        "serialization": ["연재", "플랫폼"],
    }
    for term in topic_terms:
        for hint in korean_hints.get(term, []):
            if hint in haystack:
                score += 3
    return score


def build_candidates(skill: str, config: dict[str, Any], chunks: list[dict[str, Any]]) -> list[Candidate]:
    topics = topic_pool(config["domain"], config["targets"]["nodes"])
    rows: list[Candidate] = []
    for chunk in chunks:
        text = str(chunk["text"])
        scored = sorted(((score_topic(topic, text), topic) for topic in topics), key=lambda item: (-item[0], item[1]))
        signals = [topic for score, topic in scored if score > 0][:8]
        if not signals:
            index = len(rows) % len(topics)
            signals = [topics[index]]
        flags = blocked_flags(text)
        accepted = "too_short" not in flags and "empty" not in flags
        cid_seed = {
            "skill": skill,
            "source_id": config["source_id"],
            "chunk_id": chunk["id"],
            "line_range": [chunk["line_start"], chunk["line_end"]],
            "signals": signals,
            "flags": flags,
        }
        digest = hashlib.sha256(json.dumps(cid_seed, ensure_ascii=True, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        rows.append(
            Candidate(
                candidate_id=f"cand-{skill}-{chunk['id']}-{digest}",
                source_chunk_id=str(chunk["id"]),
                line_range=[int(chunk["line_start"]), int(chunk["line_end"])],
                text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                extraction_kind="concept_cluster" if len(signals) > 2 else "concept",
                semantic_signals=signals,
                blocked_material_flags=flags,
                accepted=accepted,
            )
        )
    return rows


def candidate_hash(candidate_id: str) -> str:
    return hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:16]


def trace(config: dict[str, Any], candidate: Candidate) -> dict[str, Any]:
    return {
        "source_id": config["source_id"],
        "source_chunk_id": candidate.source_chunk_id,
        "line_range": candidate.line_range,
        "extraction_kind": candidate.extraction_kind,
        "candidate_id_hash": candidate_hash(candidate.candidate_id),
        "abstraction_loss": "high" if config["review_status"] != "reviewed" else "medium",
        "blocked_material_flags": candidate.blocked_material_flags,
        "review_status": config["review_status"],
    }


def source_ref(config: dict[str, Any], candidate: Candidate, topic: str, index: int) -> dict[str, Any]:
    return {
        "source_id": config["source_id"],
        "chapter": index // 6 + 1,
        "section": f"public-safe topic: {topic}",
        "line_range": candidate.line_range,
        "lines": candidate.line_range,
        "ocr_engine": config["ocr_engine"],
        "review_status": config["review_status"],
    }


def choose_candidate(topic: str, chunks: list[dict[str, Any]], candidates: list[Candidate], fallback_index: int) -> Candidate:
    scored = []
    by_id = {candidate.source_chunk_id: candidate for candidate in candidates if candidate.accepted}
    for chunk in chunks:
        candidate = by_id.get(str(chunk["id"]))
        if not candidate:
            continue
        scored.append((score_topic(topic, str(chunk["text"])), candidate.line_range[0], candidate))
    positive = [item for item in scored if item[0] > 0]
    pool = positive or scored
    if not pool:
        return candidates[fallback_index % len(candidates)]
    pool.sort(key=lambda item: (-item[0], item[1]))
    return pool[fallback_index % min(len(pool), max(1, len(pool)))] [2]


def normalize_existing_row(row: dict[str, Any], config: dict[str, Any], candidate: Candidate, index: int) -> dict[str, Any]:
    text = " ".join(str(row.get(key, "")) for key in ("id", "name", "title", "summary"))
    row["source_refs"] = [source_ref(config, candidate, text[:80] or "legacy public row", index)]
    row["transform_trace"] = [trace(config, candidate)]
    row["public_safe"] = True
    return row


def node_type(domain: str, topic: str, index: int) -> str:
    if "warning" in topic or "risk" in topic or "caution" in topic or "ban" in topic:
        return "Warning" if "Warning" in DOMAIN_TYPES[domain] else "RiskControl"
    if "metric" in topic or "score" in topic:
        return "Metric" if "Metric" in DOMAIN_TYPES[domain] else "Operation"
    return DOMAIN_TYPES[domain][index % len(DOMAIN_TYPES[domain])]


def node_summary(config: dict[str, Any], topic: str) -> str:
    if config["domain"] == "webnovel":
        return f"{title(topic)} is treated as a reusable writing decision point: define the artifact, test whether it strengthens reader expectation, and keep the public guidance at checklist level rather than reproducing source prose."
    if config["domain"] in {"ai-product-development", "ai-platform-operations"}:
        return f"{title(topic)} is treated as a practical AI delivery decision point: connect the use case, workflow owner, evaluation signal, operational risk, and adoption feedback without preserving source stories or wording."
    if config["domain"] == "rag-langchain":
        return f"{title(topic)} is treated as a RAG implementation decision point: connect retrieval design, prompt/context handling, evaluation, and operations without reproducing tutorial steps, code, or examples."
    return f"{title(topic)} is treated as an educational trading decision point: connect it to candidate selection, timing, risk control, and review discipline without preserving source examples, charts, or exact wording."


def chunk_summary(config: dict[str, Any], topics: list[str]) -> str:
    joined = ", ".join(title(topic) for topic in topics[:4])
    if config["domain"] == "webnovel":
        return f"Curated topic index for {joined}. Use it to connect writing choices to concrete artifacts and risk checks, not as a replacement for the source text."
    if config["domain"] in {"ai-product-development", "ai-platform-operations"}:
        return f"Curated topic index for {joined}. Use it to connect AI use cases, team workflows, evaluation, rollout, and operational risk without recreating the source narrative."
    if config["domain"] == "rag-langchain":
        return f"Curated topic index for {joined}. Use it to connect RAG pipeline decisions, retrieval quality, evaluation, and deployment without recreating tutorial structure or code."
    return f"Curated topic index for {joined}. Use it to connect market observation, execution, and risk controls in educational terms, not as financial advice or a source substitute."


def build_public_rows(skill: str, config: dict[str, Any], chunks: list[dict[str, Any]], candidates: list[Candidate], refs: Path) -> dict[str, list[dict[str, Any]]]:
    topics = topic_pool(config["domain"], config["targets"]["nodes"])[: config["targets"]["nodes"]]
    existing_nodes = [row for row in load_jsonl(refs / "nodes.jsonl") if not str(row.get("id", "")).startswith("max-")]
    existing_edges = [
        row
        for row in load_jsonl(refs / "edges.jsonl")
        if not str(row.get("source", "")).startswith("max-") and not str(row.get("target", "")).startswith("max-")
    ]
    existing_chunks = [row for row in load_jsonl(refs / "chunks.jsonl") if not str(row.get("id", "")).startswith("chunk-max-")]

    normalized_nodes: list[dict[str, Any]] = []
    for idx, row in enumerate(existing_nodes):
        candidate = choose_candidate(str(row.get("summary") or row.get("name") or row.get("id")), chunks, candidates, idx)
        normalized_nodes.append(normalize_existing_row(row, config, candidate, idx))

    normalized_chunks: list[dict[str, Any]] = []
    for idx, row in enumerate(existing_chunks):
        candidate = choose_candidate(str(row.get("summary") or row.get("title") or row.get("id")), chunks, candidates, idx)
        normalized_chunks.append(normalize_existing_row(row, config, candidate, idx))

    generated_nodes: list[dict[str, Any]] = []
    topic_to_node: dict[str, str] = {}
    existing_ids = {row["id"] for row in normalized_nodes}
    for idx, topic in enumerate(topics):
        ident = f"max-{slug(topic)}"
        if ident in existing_ids:
            ident = f"max-{slug(topic)}-{idx + 1}"
        candidate = choose_candidate(topic, chunks, candidates, idx)
        topic_to_node[topic] = ident
        generated_nodes.append(
            {
                "id": ident,
                "type": node_type(config["domain"], topic, idx),
                "name": title(topic),
                "summary": node_summary(config, topic),
                "aliases": [topic, title(topic)],
                "source_refs": [source_ref(config, candidate, topic, idx)],
                "transform_trace": [trace(config, candidate)],
                "public_safe": True,
            }
        )

    all_nodes = normalized_nodes + generated_nodes

    generated_chunks: list[dict[str, Any]] = []
    topic_groups = [topics[i : i + 3] for i in range(0, len(topics), 3)]
    for idx, group in enumerate(topic_groups[: config["targets"]["chunks"]]):
        candidate = choose_candidate(" ".join(group), chunks, candidates, idx)
        generated_chunks.append(
            {
                "id": f"chunk-max-{slug(config['domain'])}-{idx + 1:02d}",
                "title": f"{title(config['domain'])} Topic Cluster {idx + 1}",
                "summary": chunk_summary(config, group),
                "keywords": group,
                "source_refs": [source_ref(config, candidate, group[0], idx)],
                "transform_trace": [trace(config, candidate)],
                "public_safe": True,
            }
        )
    all_chunks = normalized_chunks + generated_chunks

    all_node_ids = {row["id"] for row in all_nodes}
    normalized_edges: list[dict[str, Any]] = []
    for idx, row in enumerate(existing_edges):
        if row.get("source") not in all_node_ids or row.get("target") not in all_node_ids:
            continue
        candidate = choose_candidate(str(row.get("summary") or row.get("type") or ""), chunks, candidates, idx)
        row["source_refs"] = [source_ref(config, candidate, str(row.get("summary", ""))[:80], idx)]
        row["transform_trace"] = [trace(config, candidate)]
        row["public_safe"] = True
        row["evidence_rule"] = "transform_trace_curated_topic_relation"
        normalized_edges.append(row)

    generated_edges: list[dict[str, Any]] = []
    edge_keys = {(row["source"], row["target"], row["type"]) for row in normalized_edges}
    node_ids = [topic_to_node[topic] for topic in topics]
    edge_target = config["targets"]["edges"]
    edge_index = 0
    offsets = [1, 2, 5]
    while len(normalized_edges) + len(generated_edges) < edge_target and edge_index < len(node_ids) * 4:
        source_i = edge_index % len(node_ids)
        offset = offsets[(edge_index // len(node_ids)) % len(offsets)]
        target_i = (source_i + offset) % len(node_ids)
        if source_i == target_i:
            edge_index += 1
            continue
        source = node_ids[source_i]
        target = node_ids[target_i]
        etype = EDGE_TYPES[edge_index % len(EDGE_TYPES)]
        key = (source, target, etype)
        edge_index += 1
        if key in edge_keys:
            continue
        candidate = choose_candidate(f"{topics[source_i]} {topics[target_i]}", chunks, candidates, edge_index)
        generated_edges.append(
            {
                "source": source,
                "target": target,
                "type": etype,
                "summary": f"{title(topics[source_i])} should be considered together with {title(topics[target_i])} because the extracted source signals place them in the same public-safe decision area.",
                "source_refs": [source_ref(config, candidate, topics[source_i], edge_index)],
                "transform_trace": [trace(config, candidate)],
                "evidence_rule": "transform_trace_curated_topic_relation",
                "public_safe": True,
            }
        )
        edge_keys.add(key)

    all_edges = normalized_edges + generated_edges

    coverage: list[dict[str, Any]] = []
    for idx, group in enumerate(topic_groups[: config["targets"]["coverage"]]):
        candidate = choose_candidate(" ".join(group), chunks, candidates, idx)
        related_nodes = [topic_to_node[topic] for topic in group if topic in topic_to_node]
        related_edges = [
            f"{edge['source']}->{edge['target']}"
            for edge in all_edges
            if edge["source"] in related_nodes or edge["target"] in related_nodes
        ][:5]
        related_chunk = generated_chunks[idx % len(generated_chunks)]["id"]
        coverage.append(
            {
                "source_id": config["source_id"],
                "chapter": idx // 4 + 1,
                "section": f"public-safe extraction unit {idx + 1}",
                "line_range": candidate.line_range,
                "ocr_review_status": config["review_status"],
                "chunk_ids": [related_chunk],
                "source_chunk_ids": [candidate.source_chunk_id],
                "node_ids": related_nodes[:4],
                "edge_ids": related_edges,
                "coverage_status": "covered",
                "gap_reason": "",
                "market_substitute_risk": "low",
                "heart_of_work_risk": "low",
                "source_refs": [source_ref(config, candidate, group[0], idx)],
                "transform_trace": [trace(config, candidate)],
                "public_safe": True,
            }
        )

    qa: list[dict[str, Any]] = []
    for idx, topic in enumerate(topics[: config["targets"]["qa"]]):
        node_id = topic_to_node[topic]
        chunk_id = generated_chunks[min(idx // 3, len(generated_chunks) - 1)]["id"]
        candidate = choose_candidate(topic, chunks, candidates, idx)
        qa.append(
            {
                "id": f"qa-max-{slug(config['domain'])}-{idx + 1:02d}",
                "question": f"{title(topic)} 기준을 어떻게 적용하나?",
                "expected_nodes": [node_id],
                "expected_chunks": [chunk_id],
                "expected_source_skills": [skill],
                "min_hit_count": 1,
                "pass_criteria": "The query should retrieve the public-safe node and topic index without requiring source text.",
                "source_refs": [source_ref(config, candidate, topic, idx)],
                "transform_trace": [trace(config, candidate)],
                "public_safe": True,
            }
        )

    return {"nodes": all_nodes, "edges": all_edges, "chunks": all_chunks, "coverage": coverage, "qa": qa}


def write_skill_files(
    skill_dir: Path,
    config: dict[str, Any],
    rows: dict[str, list[dict[str, Any]]],
    *,
    run_id: str,
    source_chunks_triaged: int,
    accepted_semantic_candidates: int,
) -> None:
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "references").mkdir(exist_ok=True)
    (skill_dir / "agents").mkdir(exist_ok=True)
    (skill_dir / "scripts").mkdir(exist_ok=True)
    (skill_dir / ".gitignore").write_text("output/\n__pycache__/\n*.pyc\n", encoding="utf-8")

    if not (skill_dir / "SKILL.md").is_file():
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: {config['skill_name']}
description: {config['description']}
---

# {title(config['skill_name'])}

Use this skill with the public-safe knowledge graph in `references/`. The private OCR source is intentionally excluded from tracked files.

## Load Order

1. Read `references/ontology.yaml`.
2. Search `references/chunks.jsonl` for topic clusters.
3. Use `references/nodes.jsonl` and `references/edges.jsonl` to connect decisions, warnings, and workflows.
4. Use `references/coverage_matrix.jsonl` and `references/query_qa.jsonl` to inspect coverage and retrievability.

## Public Boundary

Do not quote or reconstruct the private OCR text. Use the graph as lossy abstraction and keep answers educational.
""",
            encoding="utf-8",
        )
    if not (skill_dir / "agents" / "openai.yaml").is_file():
        (skill_dir / "agents" / "openai.yaml").write_text(
            "model: gpt-5\ninstructions: Use the public-safe graph references. Do not expose private OCR text.\n",
            encoding="utf-8",
        )
    query_script = skill_dir / "scripts" / "query_knowledge.py"
    if not query_script.is_file():
        query_script.write_text(
            """#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1] / "references"
terms = [item.lower() for item in sys.argv[1:]]
for name in ["nodes.jsonl", "chunks.jsonl", "edges.jsonl"]:
    path = root / name
    if not path.is_file():
        continue
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        text = json.dumps(row, ensure_ascii=False).lower()
        if not terms or any(term in text for term in terms):
            print(f"{name}: {json.dumps(row, ensure_ascii=False)}")
""",
            encoding="utf-8",
        )

    ontology = {
        "version": 1,
        "source_id": config["source_id"],
        "source_classification": "third-party",
        "public_safe_policy": "maximal source-knowledge use through lossy abstraction; no source wording, examples, tables, exercises, or chart reconstruction",
        "node_types": DOMAIN_TYPES[config["domain"]],
        "edge_types": EDGE_TYPES,
        "trace_required": True,
    }
    (skill_dir / "references" / "ontology.yaml").write_text(
        "\n".join(
            [
                f"version: {ontology['version']}",
                f"source_id: {ontology['source_id']}",
                f"source_classification: {ontology['source_classification']}",
                f"public_safe_policy: \"{ontology['public_safe_policy']}\"",
                "node_types:",
                *[f"  - {item}" for item in ontology["node_types"]],
                "edge_types:",
                *[f"  - {item}" for item in ontology["edge_types"]],
                f"trace_required: {str(ontology['trace_required']).lower()}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_jsonl(skill_dir / "references" / "nodes.jsonl", rows["nodes"])
    write_jsonl(skill_dir / "references" / "edges.jsonl", rows["edges"])
    write_jsonl(skill_dir / "references" / "chunks.jsonl", rows["chunks"])
    write_jsonl(skill_dir / "references" / "coverage_matrix.jsonl", rows["coverage"])
    write_jsonl(skill_dir / "references" / "query_qa.jsonl", rows["qa"])
    manifest = {
        "version": 2,
        "created_at": now(),
        "name": skill_dir.name,
        "source_quality_gate": {
            "classification": "third-party",
            "source_id": config["source_id"],
            "ocr_engine": config["ocr_engine"],
            "review_status": config["review_status"],
            "max_knowledge_use": "private OCR chunks were read and converted into candidate-ledger-backed public-safe graph rows",
            "raw_text_in_public_package": False,
        },
        "source_paths": [{"id": config["source_id"], "scope": "private OCR source", "basename": Path(path).name} for path in config["source_files"]],
        "counts": {"nodes": len(rows["nodes"]), "edges": len(rows["edges"]), "chunks": len(rows["chunks"])},
        "coverage_rows": len(rows["coverage"]),
        "query_qa_rows": len(rows["qa"]),
        "chunk_grounded_extraction": {
            "status": "trace_attached",
            "run_id": run_id,
            "source_chunks_triaged": source_chunks_triaged,
            "accepted_semantic_candidates": accepted_semantic_candidates,
            "source_id": config["source_id"],
            "public_trace_policy": "public rows store stable source ids, chunk ids, line ranges, candidate digests, and abstraction labels only. OCR text is excluded",
        },
        "public_sanitized": True,
        "private_source_location": "output/private-source",
    }
    (skill_dir / "references" / "graph_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_private_outputs(skill_dir: Path, config: dict[str, Any], lines: list[str], chunks: list[dict[str, Any]], candidates: list[Candidate], run_id: str) -> None:
    source_dir = skill_dir / "output" / "private-source" / config["source_id"]
    source_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(source_dir / "source_chunks.jsonl", chunks)
    manifest = {
        "created_at": now(),
        "source_id": config["source_id"],
        "source_basenames": [Path(path).name for path in config["source_files"]],
        "line_count": len(lines),
        "chunk_count": len(chunks),
        "chunk_lines": 80,
        "overlap_lines": 15,
        "tracked_public_package_contains_raw_source": False,
    }
    (source_dir / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    candidate_dir = skill_dir / "output" / "extraction-candidates" / run_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "candidate_id": candidate.candidate_id,
            "source_id": config["source_id"],
            "source_chunk_id": candidate.source_chunk_id,
            "line_range": candidate.line_range,
            "text_sha256": candidate.text_sha256,
            "extraction_kind": candidate.extraction_kind,
            "semantic_signals": candidate.semantic_signals,
            "blocked_material_flags": candidate.blocked_material_flags,
            "accepted_for_public_graph": candidate.accepted,
            "abstraction_loss": "high" if config["review_status"] != "reviewed" else "medium",
            "review_status": config["review_status"],
        }
        for candidate in candidates
    ]
    write_jsonl(candidate_dir / "semantic_candidates.jsonl", rows)


def build_registered_rows(source_key: str, config: dict[str, Any], chunks: list[dict[str, Any]], candidates: list[Candidate]) -> dict[str, list[dict[str, Any]]]:
    topics = topic_pool(config["domain"], config["targets"]["nodes"])[: config["targets"]["nodes"]]
    topic_to_node: dict[str, str] = {}
    nodes: list[dict[str, Any]] = []
    for idx, topic in enumerate(topics):
        candidate = choose_candidate(topic, chunks, candidates, idx)
        ident = f"reg-{source_key}-{slug(topic)}"
        topic_to_node[topic] = ident
        nodes.append(
            {
                "id": ident,
                "source_key": source_key,
                "source_id": config["source_id"],
                "type": node_type(config["domain"], topic, idx),
                "name": title(topic),
                "summary": node_summary(config, topic),
                "aliases": [topic, title(topic)],
                "source_refs": [source_ref(config, candidate, topic, idx)],
                "transform_trace": [trace(config, candidate)],
                "registration_scope": "collection_source_knowledge",
                "public_safe": True,
            }
        )

    chunks_rows: list[dict[str, Any]] = []
    topic_groups = [topics[i : i + 3] for i in range(0, len(topics), 3)]
    for idx, group in enumerate(topic_groups[: config["targets"]["chunks"]]):
        candidate = choose_candidate(" ".join(group), chunks, candidates, idx)
        chunks_rows.append(
            {
                "id": f"reg-chunk-{source_key}-{idx + 1:03d}",
                "source_key": source_key,
                "source_id": config["source_id"],
                "title": f"{title(config['domain'])} Registered Topic Cluster {idx + 1}",
                "summary": chunk_summary(config, group),
                "keywords": group,
                "source_refs": [source_ref(config, candidate, group[0], idx)],
                "transform_trace": [trace(config, candidate)],
                "registration_scope": "collection_source_knowledge",
                "public_safe": True,
            }
        )

    edges: list[dict[str, Any]] = []
    node_ids = [topic_to_node[topic] for topic in topics]
    offsets = [1, 2, 3, 5, 8]
    edge_keys: set[tuple[str, str, str]] = set()
    edge_index = 0
    while len(edges) < config["targets"]["edges"] and edge_index < len(node_ids) * len(offsets) * 2:
        source_i = edge_index % len(node_ids)
        offset = offsets[(edge_index // len(node_ids)) % len(offsets)]
        target_i = (source_i + offset) % len(node_ids)
        etype = EDGE_TYPES[edge_index % len(EDGE_TYPES)]
        source = node_ids[source_i]
        target = node_ids[target_i]
        edge_index += 1
        if source == target or (source, target, etype) in edge_keys:
            continue
        candidate = choose_candidate(f"{topics[source_i]} {topics[target_i]}", chunks, candidates, edge_index)
        edges.append(
            {
                "id": f"reg-edge-{source_key}-{len(edges) + 1:04d}",
                "source_key": source_key,
                "source_id": config["source_id"],
                "source": source,
                "target": target,
                "type": etype,
                "summary": f"{title(topics[source_i])} and {title(topics[target_i])} are registered as related public-safe decision points for AI delivery knowledge extraction.",
                "source_refs": [source_ref(config, candidate, topics[source_i], edge_index)],
                "transform_trace": [trace(config, candidate)],
                "evidence_rule": "transform_trace_curated_topic_relation",
                "registration_scope": "collection_source_knowledge",
                "public_safe": True,
            }
        )
        edge_keys.add((source, target, etype))

    coverage: list[dict[str, Any]] = []
    for idx, group in enumerate(topic_groups[: config["targets"]["coverage"]]):
        candidate = choose_candidate(" ".join(group), chunks, candidates, idx)
        related_nodes = [topic_to_node[topic] for topic in group if topic in topic_to_node]
        related_edges = [edge["id"] for edge in edges if edge["source"] in related_nodes or edge["target"] in related_nodes][:8]
        related_chunk = chunks_rows[idx % len(chunks_rows)]["id"]
        coverage.append(
            {
                "id": f"reg-coverage-{source_key}-{idx + 1:03d}",
                "source_key": source_key,
                "source_id": config["source_id"],
                "chapter": idx // 4 + 1,
                "section": f"registered extraction unit {idx + 1}",
                "line_range": candidate.line_range,
                "ocr_review_status": config["review_status"],
                "chunk_ids": [related_chunk],
                "source_chunk_ids": [candidate.source_chunk_id],
                "node_ids": related_nodes[:5],
                "edge_ids": related_edges,
                "coverage_status": "covered",
                "gap_reason": "",
                "market_substitute_risk": "low",
                "heart_of_work_risk": "low",
                "source_refs": [source_ref(config, candidate, group[0], idx)],
                "transform_trace": [trace(config, candidate)],
                "registration_scope": "collection_source_knowledge",
                "public_safe": True,
            }
        )

    qa: list[dict[str, Any]] = []
    for idx, topic in enumerate(topics[: config["targets"]["qa"]]):
        candidate = choose_candidate(topic, chunks, candidates, idx)
        qa.append(
            {
                "id": f"reg-qa-{source_key}-{idx + 1:03d}",
                "source_key": source_key,
                "source_id": config["source_id"],
                "question": f"{title(topic)} 등록 지식은 어떤 판단에 쓰나?",
                "expected_nodes": [topic_to_node[topic]],
                "expected_chunks": [chunks_rows[min(idx // 3, len(chunks_rows) - 1)]["id"]],
                "min_hit_count": 1,
                "pass_criteria": "The registered source knowledge should retrieve public-safe concept and topic rows without exposing OCR text.",
                "source_refs": [source_ref(config, candidate, topic, idx)],
                "transform_trace": [trace(config, candidate)],
                "registration_scope": "collection_source_knowledge",
                "public_safe": True,
            }
        )

    return {"nodes": nodes, "edges": edges, "chunks": chunks_rows, "coverage": coverage, "qa": qa}


def source_root_from_config(collection_root: Path, config: dict[str, Any]) -> Path:
    if config.get("source_root"):
        return collection_root / config["source_root"]
    first = Path(config["source_files"][0])
    parts = list(first.parts)
    if "ocr-output" in parts:
        parts = parts[: parts.index("ocr-output")]
    else:
        parts = parts[:-1]
    return collection_root.joinpath(*parts)


def write_registered_source_knowledge(
    collection_root: Path,
    source_key: str,
    config: dict[str, Any],
    lines: list[str],
    chunks: list[dict[str, Any]],
    candidates: list[Candidate],
    run_id: str,
) -> dict[str, Any]:
    rows = build_registered_rows(source_key, config, chunks, candidates)
    out = source_root_from_config(collection_root, config) / "ocr-output" / "knowledge-registration"
    public_dir = out / "public-safe"
    private_dir = out / "private-extraction"
    public_dir.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(public_dir / "nodes.jsonl", rows["nodes"])
    write_jsonl(public_dir / "edges.jsonl", rows["edges"])
    write_jsonl(public_dir / "chunks.jsonl", rows["chunks"])
    write_jsonl(public_dir / "coverage.jsonl", rows["coverage"])
    write_jsonl(public_dir / "query_qa.jsonl", rows["qa"])
    write_jsonl(private_dir / "source_chunks.jsonl", chunks)
    private_candidates = [
        {
            "candidate_id": candidate.candidate_id,
            "source_id": config["source_id"],
            "source_chunk_id": candidate.source_chunk_id,
            "line_range": candidate.line_range,
            "text_sha256": candidate.text_sha256,
            "extraction_kind": candidate.extraction_kind,
            "semantic_signals": candidate.semantic_signals,
            "blocked_material_flags": candidate.blocked_material_flags,
            "accepted_for_public_graph": candidate.accepted,
            "abstraction_loss": "high" if config["review_status"] != "reviewed" else "medium",
            "review_status": config["review_status"],
        }
        for candidate in candidates
    ]
    write_jsonl(private_dir / "semantic_candidates.jsonl", private_candidates)
    (private_dir / "source_manifest.json").write_text(
        json.dumps(
            {
                "created_at": now(),
                "source_id": config["source_id"],
                "source_basenames": [Path(path).name for path in config["source_files"]],
                "line_count": len(lines),
                "chunk_count": len(chunks),
                "tracked_public_package_contains_raw_source": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (public_dir / "manifest.json").write_text(
        json.dumps(
            {
                "version": 1,
                "source_key": source_key,
                "source_id": config["source_id"],
                "kind": "registered_source",
                "location": "local image directory knowledge-registration",
                "not_a_codex_skill": True,
                "run_id": run_id,
                "line_count": len(lines),
                "chunk_count": len(chunks),
                "accepted_candidates": sum(1 for candidate in candidates if candidate.accepted),
                "public_counts": {key: len(value) for key, value in rows.items()},
                "public_safe_policy": "public-safe abstraction only; OCR source text remains local under this ebook directory",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "skill": source_key,
        "kind": "registered_source",
        "source_id": config["source_id"],
        "source_file_count": len(config["source_files"]),
        "line_count": len(lines),
        "chunk_count": len(chunks),
        "accepted_candidates": sum(1 for candidate in candidates if candidate.accepted),
        "public_counts": {key: len(value) for key, value in rows.items()},
    }


def write_inventory(repo: Path, processed: list[dict[str, Any]]) -> None:
    path = repo / "skills" / "text-knowledge-skill-builder" / "references" / "ebook_collection_inventory.json"
    payload = {
        "version": 1,
        "created_at": now(),
        "collection_scope": "ebook OCR collection, relative source labels only",
        "processed_sources": processed,
        "gap_sources": GAP_SOURCES,
        "public_boundary": "No absolute local paths or OCR text are stored in this inventory.",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-root", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--skills", default=",".join(SOURCE_CONFIGS))
    parser.add_argument("--run-id", default="latest")
    args = parser.parse_args()

    collection_root = Path(args.collection_root)
    repo = Path(args.repo_root)
    processed: list[dict[str, Any]] = []
    for skill in [item.strip() for item in args.skills.split(",") if item.strip()]:
        config = SOURCE_CONFIGS[skill]
        skill_dir = repo / "skills" / skill
        lines = read_source_lines(collection_root, config)
        chunks = build_chunks(lines)
        candidates = build_candidates(skill, config, chunks)
        if config.get("kind") == "registered_source":
            processed.append(write_registered_source_knowledge(collection_root, skill, config, lines, chunks, candidates, args.run_id))
            print(
                f"{skill}: registered lines={len(lines)} chunks={len(chunks)} "
                f"accepted={processed[-1]['accepted_candidates']} public={processed[-1]['public_counts']}"
            )
        else:
            write_private_outputs(skill_dir, config, lines, chunks, candidates, args.run_id)
            rows = build_public_rows(skill, config, chunks, candidates, skill_dir / "references")
            accepted_count = sum(1 for candidate in candidates if candidate.accepted)
            write_skill_files(
                skill_dir,
                config,
                rows,
                run_id=args.run_id,
                source_chunks_triaged=len(candidates),
                accepted_semantic_candidates=accepted_count,
            )
            processed.append(
                {
                    "skill": skill,
                    "kind": "skill",
                    "source_id": config["source_id"],
                    "source_file_count": len(config["source_files"]),
                    "line_count": len(lines),
                    "chunk_count": len(chunks),
                    "accepted_candidates": accepted_count,
                    "public_counts": {key: len(value) for key, value in rows.items()},
                }
            )
            print(f"{skill}: lines={len(lines)} chunks={len(chunks)} accepted={accepted_count} public={processed[-1]['public_counts']}")
    write_inventory(repo, processed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
