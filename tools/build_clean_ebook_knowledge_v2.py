#!/usr/bin/env python3
"""Rebuild ebook knowledge packs from final-clean-v2 OCR outputs.

Registered repository skills are refreshed in-place. Non-registered sources
write source-local knowledge-registration packs only.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any


def load_builder(repo: Path):
    path = repo / "tools" / "build_ebook_collection_knowledge.py"
    spec = importlib.util.spec_from_file_location("ebook_knowledge_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load builder: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["ebook_knowledge_builder"] = module
    spec.loader.exec_module(module)
    return module


ENGINEERING_TYPES = ["Concept", "Principle", "Pattern", "Decision", "Workflow", "Warning", "Practice", "Boundary"]
TRADING_TYPES = ["Concept", "SelectionCriterion", "RiskControl", "Workflow", "Warning", "Practice"]


TOPICS: dict[str, list[str]] = {
    "domain-driven-design": [
        "도메인 모델 domain model", "유비쿼터스 언어 ubiquitous language", "바운디드 컨텍스트 bounded context",
        "컨텍스트 맵 context map", "서브도메인 subdomain", "핵심 도메인 core domain", "지원 도메인 supporting domain",
        "일반 도메인 generic domain", "전략적 설계 strategic design", "전술적 설계 tactical design",
        "애그리거트 aggregate", "엔티티 entity", "값 객체 value object", "도메인 서비스 domain service",
        "도메인 이벤트 domain event", "리포지터리 repository", "팩토리 factory", "모듈 module",
        "일관성 경계 consistency boundary", "트랜잭션 경계 transaction boundary", "이벤트 스토밍 event storming",
        "컨텍스트 통합 context integration", "공유 커널 shared kernel", "고객 공급자 customer supplier",
        "순응자 conformist", "부패 방지 계층 anticorruption layer", "오픈 호스트 서비스 open host service",
        "발행된 언어 published language", "분리된 방식 separate ways", "거대한 진흙덩어리 big ball of mud",
        "CQRS", "event sourcing", "마이크로서비스 microservice", "도메인 주도 조직", "모델 탐색",
        "언어 정제", "경계 발견", "협업 설계", "복잡성 분리", "레거시 통합", "비즈니스 역량",
        "의사결정 기록", "모델 리팩터링", "도메인 전문가 협업", "서비스 경계", "데이터 소유권",
        "통합 이벤트", "명령 command", "정책 policy", "프로세스 모델", "시나리오 분석",
    ],
    "fastapi-clean-architecture": [
        "FastAPI", "APIRouter", "Depends dependency injection", "Pydantic schema", "request response model",
        "clean architecture", "dependency rule", "dependency inversion", "domain layer", "application layer",
        "interface layer", "infrastructure layer", "repository pattern", "service layer", "use case",
        "SQLAlchemy", "Alembic migration", "database session", "transaction boundary", "DTO schema boundary",
        "authentication", "authorization", "JWT token", "password hashing", "CRUD endpoint", "exception handling",
        "OpenAPI docs", "Uvicorn", "Docker", "MySQL", "test client", "unit test", "integration test",
        "settings configuration", "environment variable", "router module", "project structure", "domain entity",
        "value object", "interface adapter", "persistence adapter", "API boundary", "dependency provider",
        "security dependency", "pagination", "validation error", "response status", "layer violation warning",
    ],
    "modern-java": [
        "lambda expression", "functional interface", "method reference", "stream pipeline", "collector",
        "Optional", "default method", "behavior parameterization", "predicate function consumer supplier",
        "map filter reduce", "parallel stream", "CompletableFuture", "future composition", "reactive programming",
        "date time API", "LocalDate LocalDateTime", "interface evolution", "immutability", "side effect warning",
        "lazy evaluation", "short circuiting", "flatMap", "groupingBy partitioningBy", "custom collector",
        "spliterator", "fork join", "concurrency", "asynchronous pipeline", "exception handling",
        "pattern matching", "sealed class", "record", "module system", "Java API evolution",
        "testability", "readability", "performance tradeoff", "stream debug", "null handling", "domain model",
        "collection processing", "imperative to functional refactor", "thread pool", "completion stage",
    ],
    "python-architecture": [
        "domain model", "repository pattern", "service layer", "unit of work", "aggregate", "entity",
        "value object", "command handler", "event bus", "domain event", "message bus", "CQRS",
        "dependency inversion", "ports and adapters", "adapter", "ORM mapping", "SQLAlchemy",
        "Flask API", "FastAPI boundary", "Django boundary", "testing pyramid", "unit test", "integration test",
        "fake repository", "mock boundary", "transaction boundary", "application service", "bootstrap",
        "configuration", "dependency injection", "allocation example", "batch refactor", "event-driven architecture",
        "microservice boundary", "monolith boundary", "REST API", "serialization", "database session",
        "concurrency", "message broker", "containerization", "observability", "logging", "metrics",
        "deployment", "twelve factor app", "packaging", "maintainability", "coupling", "cohesion",
    ],
    "tidy-first": [
        "tidy first", "behavior change", "structural change", "separate changes", "small steps",
        "reversibility", "coupling", "cohesion", "cost of change", "option value", "batch size",
        "refactoring", "rename", "extract helper", "guard clause", "normalize symmetry", "dead code removal",
        "readability", "local reasoning", "change sequencing", "test before behavior", "reviewability",
        "commit discipline", "safe cleanup", "abstraction timing", "premature abstraction warning",
        "design pressure", "team agreement", "economic tradeoff", "workflow habit", "code smell",
        "duplication", "dependency cleanup", "interface simplification", "call site clarity",
        "decision point", "risk reduction", "feedback loop", "software design", "maintenance",
    ],
    "stock-chart-reading": [
        "chart reading", "price action", "moving average", "candlestick", "support resistance",
        "trend line", "breakout", "pullback", "volume confirmation", "gap behavior", "opening price",
        "closing price", "market psychology", "false breakout", "stop loss", "entry timing",
        "profit taking", "risk reward", "watchlist", "leader stock", "sector theme", "news catalyst",
        "liquidity", "volatility", "position size", "trade journal", "chart pattern", "sideways range",
        "momentum", "reversal", "continuation", "buyer pressure", "seller pressure", "educational not advice",
    ],
    "stock-investing": [
        "investment philosophy", "long term survival", "risk management", "market cycle", "portfolio discipline",
        "trend following", "loss control", "cash management", "experience based judgment", "technical indicator",
        "trade routine", "position sizing", "patience", "crisis response", "drawdown", "compound return",
        "psychology", "rule consistency", "stock selection", "market observation", "high probability setup",
        "sell discipline", "habit", "review", "age and investing", "educational not advice",
    ],
    "wyckoff-trading": [
        "Wyckoff method", "market cycle", "accumulation", "markup", "distribution", "markdown",
        "composite operator", "smart money", "supply and demand", "effort versus result",
        "cause and effect", "law of supply and demand", "law of effort and result", "price volume relationship",
        "trading range", "support resistance", "spring", "upthrust", "sign of strength", "sign of weakness",
        "last point of support", "last point of supply", "secondary test", "selling climax", "automatic rally",
        "automatic reaction", "preliminary support", "preliminary supply", "buying climax", "phase A",
        "phase B", "phase C", "phase D", "phase E", "volume spread analysis", "absorption",
        "reaccumulation", "redistribution", "breakout confirmation", "failed breakout", "risk control",
        "entry timing", "stop placement", "position sizing", "trade scenario", "chart annotation",
        "relative strength", "sector leadership", "trend context", "volume divergence", "no demand",
        "no supply", "shakeout", "test", "back up to edge of creek", "jump across creek",
        "ice line", "creek", "market structure", "educational not advice",
    ],
}


CLEAN_CONFIGS: dict[str, dict[str, Any]] = {
    "daily-webnovel-writing-knowledge-skill": {
        "skill_name": "daily-webnovel-writing-knowledge",
        "domain": "webnovel",
        "source_id": "daily-webnovel-writing-clean-v2",
        "review_status": "final_clean_v2_auto_manual_remaining_2",
        "ocr_engine": "moonshotnote_ocr_v2_paddle_final_clean",
        "source_files": ["ocr-output/final-clean-v2/books/창작__매일 웹소설 쓰기.clean.md"],
        "targets": {"nodes": 90, "edges": 155, "chunks": 35, "coverage": 45, "qa": 45},
        "description": "Use this skill for Korean webnovel writing planning, serialization strategy, genre-market fit, character design, episode structure, readability, cliffhangers, metrics, submission, contracts, and sustainable completion habits.",
    },
    "domain-driven-design-first-steps": {
        "skill_name": "domain-driven-design-first-steps",
        "domain": "domain-driven-design",
        "source_id": "domain-driven-design-first-steps-clean-v2",
        "review_status": "final_clean_v2_auto_manual_remaining_2",
        "ocr_engine": "moonshotnote_ocr_v2_paddle_final_clean",
        "source_files": ["ocr-output/final-clean-v2/books/프로그래밍__도메인 주도 설계 첫걸음.clean.md"],
        "targets": {"nodes": 132, "edges": 225, "chunks": 44, "coverage": 58, "qa": 52},
        "description": "Use this public-safe Korean study skill for Domain-Driven Design first-step questions about subdomains, ubiquitous language, bounded contexts, context maps, tactical patterns, event sourcing, CQRS, event storming, microservices, event-driven architecture, and data mesh.",
    },
    "fastapi-clean-architecture": {
        "skill_name": "fastapi-clean-architecture",
        "domain": "fastapi-clean-architecture",
        "source_id": "fastapi-clean-architecture-clean-v2",
        "review_status": "final_clean_v2_auto_manual_remaining_10",
        "ocr_engine": "moonshotnote_ocr_v2_paddle_final_clean",
        "source_files": ["ocr-output/final-clean-v2/books/프로그래밍__FastAPI로 배우는 백엔드 프로그래밍 with 클린 아키텍처.clean.md"],
        "targets": {"nodes": 105, "edges": 175, "chunks": 32, "coverage": 40, "qa": 42},
        "description": "FastAPI and clean architecture study assistant backed by a public-safe graph extracted from OCR notes.",
    },
    "modern-java-in-action": {
        "skill_name": "modern-java-in-action",
        "domain": "modern-java",
        "source_id": "modern-java-in-action-clean-v2",
        "review_status": "final_clean_v2_auto_manual_remaining_3",
        "ocr_engine": "moonshotnote_ocr_v2_paddle_final_clean",
        "source_files": ["ocr-output/final-clean-v2/books/프로그래밍__모던 자바 인 액션.clean.md"],
        "targets": {"nodes": 112, "edges": 185, "chunks": 36, "coverage": 45, "qa": 42},
        "description": "Modern Java study assistant backed by a public-safe graph extracted from OCR-derived notes.",
    },
    "python-architecture-patterns": {
        "skill_name": "python-architecture-patterns",
        "domain": "python-architecture",
        "source_id": "python-architecture-patterns-clean-v2",
        "review_status": "final_clean_v2_auto_manual_remaining_24",
        "ocr_engine": "moonshotnote_ocr_v2_paddle_final_clean",
        "source_files": ["ocr-output/final-clean-v2/books/프로그래밍__파이썬 아키텍처 패턴.clean.md"],
        "targets": {"nodes": 186, "edges": 320, "chunks": 60, "coverage": 88, "qa": 64},
        "description": "Python software architecture patterns study assistant backed by public-safe OCR-derived graph knowledge.",
    },
    "teddynote-langchain-rag": {
        "skill_name": "teddynote-langchain-rag",
        "domain": "rag-langchain",
        "source_id": "teddynote-langchain-rag-clean-v2",
        "review_status": "final_clean_v2_auto_manual_remaining_74",
        "ocr_engine": "moonshotnote_ocr_v2_paddle_final_clean",
        "source_files": ["ocr-output/final-clean-v2/books/프로그래밍__테디노트의 랭체인을 활용한 RAG 비법 노트 - 기본, 심화.clean.md"],
        "targets": {"nodes": 190, "edges": 340, "chunks": 70, "coverage": 90, "qa": 65},
        "description": "Use this skill for public-safe reasoning about RAG and LangChain pipelines, document loading, splitting, embedding, vector stores, retrievers, prompts, chains, evaluation, deployment, and troubleshooting.",
    },
    "tidy-first": {
        "skill_name": "tidy-first",
        "domain": "tidy-first",
        "source_id": "tidy-first-clean-v2",
        "review_status": "final_clean_v2_auto_manual_remaining_0",
        "ocr_engine": "moonshotnote_ocr_v2_paddle_final_clean",
        "source_files": ["ocr-output/final-clean-v2/books/프로그래밍__켄트 벡의 Tidy First.clean.md"],
        "targets": {"nodes": 72, "edges": 220, "chunks": 22, "coverage": 22, "qa": 35},
        "description": "Tidy First study and engineering-decision assistant backed by a public-safe OCR-derived knowledge graph.",
    },
    "ebook-1page-stock-chart": {
        "kind": "registered_source",
        "skill_name": "ebook-1page-stock-chart",
        "domain": "stock-chart-reading",
        "source_id": "ebook-1page-stock-chart-clean-v2",
        "review_status": "final_clean_v2_auto_manual_remaining_31",
        "ocr_engine": "moonshotnote_ocr_v2_paddle_final_clean",
        "source_root": "트레이딩/1page 주가차트",
        "source_files": ["ocr-output/final-clean-v2/books/트레이딩__1page 주가차트.clean.md"],
        "targets": {"nodes": 90, "edges": 180, "chunks": 34, "coverage": 42, "qa": 40},
        "description": "Source-local public-safe knowledge registration for chart-reading study material.",
    },
    "ebook-short-term-trading-3pct": {
        "kind": "registered_source",
        "skill_name": "ebook-short-term-trading-3pct",
        "domain": "trading-3pct",
        "source_id": "ebook-short-term-trading-3pct-clean-v2",
        "review_status": "final_clean_v2_auto_manual_remaining_7",
        "ocr_engine": "moonshotnote_ocr_v2_paddle_final_clean",
        "source_root": "트레이딩/30분 투자 매일+3% 단타 수익",
        "source_files": ["ocr-output/final-clean-v2/books/트레이딩__30분 투자 매일+3% 단타 수익.clean.md"],
        "targets": {"nodes": 110, "edges": 220, "chunks": 42, "coverage": 52, "qa": 50},
        "description": "Source-local public-safe knowledge registration for short-term trading study material.",
    },
    "ebook-big-trader-leading-stock": {
        "kind": "registered_source",
        "skill_name": "ebook-big-trader-leading-stock",
        "domain": "leading-stock",
        "source_id": "ebook-big-trader-leading-stock-clean-v2",
        "review_status": "final_clean_v2_auto_manual_remaining_30",
        "ocr_engine": "moonshotnote_ocr_v2_paddle_final_clean",
        "source_root": "트레이딩/빅 트레이더의 주도주 매매법",
        "source_files": ["ocr-output/final-clean-v2/books/트레이딩__빅 트레이더의 주도주 매매법.clean.md"],
        "targets": {"nodes": 150, "edges": 300, "chunks": 56, "coverage": 70, "qa": 65},
        "description": "Source-local public-safe knowledge registration for leading-stock trading study material.",
    },
    "ebook-stock-investing-joy": {
        "kind": "registered_source",
        "skill_name": "ebook-stock-investing-joy",
        "domain": "stock-investing",
        "source_id": "ebook-stock-investing-joy-clean-v2",
        "review_status": "final_clean_v2_auto_manual_remaining_57",
        "ocr_engine": "moonshotnote_ocr_v2_paddle_final_clean",
        "source_root": "트레이딩/주식 투자의 기쁨",
        "source_files": ["ocr-output/final-clean-v2/books/트레이딩__주식 투자의 기쁨.clean.md"],
        "targets": {"nodes": 95, "edges": 190, "chunks": 36, "coverage": 45, "qa": 42},
        "description": "Source-local public-safe knowledge registration for stock investing study material.",
    },
    "ebook-stock-short-term-trading": {
        "kind": "registered_source",
        "skill_name": "ebook-stock-short-term-trading",
        "domain": "stock-short-term",
        "source_id": "ebook-stock-short-term-trading-clean-v2",
        "review_status": "final_clean_v2_auto_manual_remaining_40",
        "ocr_engine": "moonshotnote_ocr_v2_paddle_final_clean",
        "source_root": "트레이딩/주식투자 단기 트레이딩의 정석",
        "source_files": ["ocr-output/final-clean-v2/books/트레이딩__주식투자 단기 트레이딩의 정석.clean.md"],
        "targets": {"nodes": 170, "edges": 340, "chunks": 66, "coverage": 82, "qa": 75},
        "description": "Source-local public-safe knowledge registration for short-term stock trading study material.",
    },
    "ebook-daangn-ai-development": {
        "kind": "registered_source",
        "skill_name": "ebook-daangn-ai-development",
        "domain": "ai-product-development",
        "source_id": "ebook-daangn-ai-development-clean-v2",
        "review_status": "final_clean_v2_auto_manual_remaining_12",
        "ocr_engine": "moonshotnote_ocr_v2_paddle_final_clean",
        "source_root": "프로그래밍/요즘 당근 AI 개발",
        "source_files": ["ocr-output/final-clean-v2/books/프로그래밍__요즘 당근 AI 개발.clean.md"],
        "targets": {"nodes": 180, "edges": 360, "chunks": 70, "coverage": 85, "qa": 70},
        "description": "Source-local public-safe knowledge registration for practical AI product development study material.",
    },
    "ebook-woowahan-ai-development": {
        "kind": "registered_source",
        "skill_name": "ebook-woowahan-ai-development",
        "domain": "ai-platform-operations",
        "source_id": "ebook-woowahan-ai-development-clean-v2",
        "review_status": "final_clean_v2_auto_manual_remaining_20",
        "ocr_engine": "moonshotnote_ocr_v2_paddle_final_clean",
        "source_root": "프로그래밍/요즘 우아한 AI 개발",
        "source_files": ["ocr-output/final-clean-v2/books/프로그래밍__요즘 우아한 AI 개발.clean.md"],
        "targets": {"nodes": 220, "edges": 440, "chunks": 85, "coverage": 110, "qa": 80},
            "description": "Source-local public-safe knowledge registration for AI platform and operations study material.",
    },
    "ebook-wyckoff-pattern": {
        "kind": "registered_source",
        "skill_name": "ebook-wyckoff-pattern",
        "domain": "wyckoff-trading",
        "source_id": "ebook-wyckoff-pattern-clean-v2",
        "review_status": "final_clean_v2_auto_manual_remaining_45",
        "ocr_engine": "moonshotnote_ocr_v2_paddle_final_clean",
        "source_root": "트레이딩/와이코프 패턴",
        "source_files": ["트레이딩/와이코프 패턴/ocr-output/final-clean-v2/clean_ocr.md"],
        "targets": {"nodes": 130, "edges": 260, "chunks": 48, "coverage": 60, "qa": 55},
        "description": "Source-local public-safe knowledge registration for Wyckoff pattern trading study material.",
    },
}


REGISTERED_SKILLS = [
    "daily-webnovel-writing-knowledge-skill",
    "domain-driven-design-first-steps",
    "fastapi-clean-architecture",
    "modern-java-in-action",
    "python-architecture-patterns",
    "teddynote-langchain-rag",
    "tidy-first",
]

SOURCE_LOCAL_ONLY = [
    "ebook-1page-stock-chart",
    "ebook-short-term-trading-3pct",
    "ebook-big-trader-leading-stock",
    "ebook-stock-investing-joy",
    "ebook-stock-short-term-trading",
    "ebook-daangn-ai-development",
    "ebook-woowahan-ai-development",
    "ebook-wyckoff-pattern",
]


def install_domain_extensions(builder) -> None:
    builder.TOPICS.update(TOPICS)
    builder.DOMAIN_TYPES.update(
        {
            "domain-driven-design": ENGINEERING_TYPES,
            "fastapi-clean-architecture": ENGINEERING_TYPES,
            "modern-java": ENGINEERING_TYPES,
            "python-architecture": ENGINEERING_TYPES,
            "tidy-first": ENGINEERING_TYPES,
            "stock-chart-reading": TRADING_TYPES,
            "stock-investing": TRADING_TYPES,
            "wyckoff-trading": TRADING_TYPES,
        }
    )
    original_node_summary = builder.node_summary
    original_chunk_summary = builder.chunk_summary

    def node_summary(config: dict[str, Any], topic: str) -> str:
        domain = config["domain"]
        if domain in {"domain-driven-design", "fastapi-clean-architecture", "modern-java", "python-architecture", "tidy-first"}:
            return (
                f"{builder.title(topic)} is treated as a public-safe engineering knowledge point: "
                "connect the concept to design decisions, workflow boundaries, risks, and review checks "
                "without reproducing source prose, examples, code, or exercises."
            )
        if domain in {"stock-chart-reading", "stock-investing", "wyckoff-trading"}:
            return (
                f"{builder.title(topic)} is treated as educational market-analysis knowledge: "
                "connect observation, discipline, risk control, and review without preserving charts, examples, "
                "numbers, or presenting financial advice."
            )
        return original_node_summary(config, topic)

    def chunk_summary(config: dict[str, Any], topics: list[str]) -> str:
        domain = config["domain"]
        joined = ", ".join(builder.title(topic) for topic in topics[:4])
        if domain in {"domain-driven-design", "fastapi-clean-architecture", "modern-java", "python-architecture", "tidy-first"}:
            return (
                f"Curated public-safe engineering topic index for {joined}. Use it to retrieve concepts, "
                "decisions, boundaries, warnings, and workflows without recreating the source text."
            )
        if domain in {"stock-chart-reading", "stock-investing", "wyckoff-trading"}:
            return (
                f"Curated public-safe market-study topic index for {joined}. Use it for educational reasoning "
                "about observation and risk discipline, not as advice or a source substitute."
            )
        return original_chunk_summary(config, topics)

    builder.node_summary = node_summary
    builder.chunk_summary = chunk_summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-root", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--run-id", default="clean-v2")
    parser.add_argument(
        "--scope",
        choices=["all", "registered", "source-local"],
        default="all",
        help="Which source set to process.",
    )
    parser.add_argument(
        "--keys",
        default="",
        help="Comma-separated config keys to process. Overrides --scope when provided.",
    )
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    builder = load_builder(repo)
    install_domain_extensions(builder)
    builder.SOURCE_CONFIGS.clear()
    builder.SOURCE_CONFIGS.update(CLEAN_CONFIGS)

    if args.keys.strip():
        keys = [item.strip() for item in args.keys.split(",") if item.strip()]
    elif args.scope == "registered":
        keys = REGISTERED_SKILLS
    elif args.scope == "source-local":
        keys = SOURCE_LOCAL_ONLY
    else:
        keys = REGISTERED_SKILLS + SOURCE_LOCAL_ONLY

    original_argv = sys.argv[:]
    try:
        sys.argv = [
            "build_ebook_collection_knowledge.py",
            "--collection-root",
            args.collection_root,
            "--repo-root",
            str(repo),
            "--skills",
            ",".join(keys),
            "--run-id",
            args.run_id,
        ]
        return int(builder.main())
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    raise SystemExit(main())
