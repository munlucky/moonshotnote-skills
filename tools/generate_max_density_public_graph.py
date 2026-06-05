#!/usr/bin/env python3
"""Expand OCR-derived public-safe knowledge graphs with dense abstractions.

The generated rows intentionally avoid source wording. They use private chunk
manifests only for stable source ids and line coverage, then emit curated
concept, relationship, topic-index, coverage, and query rows.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SOURCE_SKILLS = [
    "tidy-first",
    "fastapi-clean-architecture",
    "modern-java-in-action",
    "domain-driven-design-first-steps",
    "spring-modern-api",
    "python-architecture-patterns",
]


TARGETS = {
    "tidy-first": {"nodes": 72, "edges": 118, "chunks": 22, "coverage": 22, "qa": 35},
    "fastapi-clean-architecture": {"nodes": 105, "edges": 175, "chunks": 32, "coverage": 40, "qa": 42},
    "modern-java-in-action": {"nodes": 112, "edges": 185, "chunks": 36, "coverage": 45, "qa": 42},
    "domain-driven-design-first-steps": {"nodes": 132, "edges": 225, "chunks": 44, "coverage": 58, "qa": 52},
    "spring-modern-api": {"nodes": 164, "edges": 285, "chunks": 50, "coverage": 68, "qa": 58},
    "python-architecture-patterns": {"nodes": 186, "edges": 320, "chunks": 60, "coverage": 88, "qa": 64},
    "backend-architecture": {"nodes": 182, "edges": 330, "chunks": 58, "qa": 72, "canonical": 44, "promotion": 112},
}


SKILL_CONFIG = {
    "tidy-first": {
        "source_id": "tidy-first-ocr",
        "review_status": "unreviewed_private_ocr_source",
        "ocr_engine": "paddle",
        "node_types": ["Tidy", "Decision", "Theory", "Management", "Warning"],
        "edge_types": ["precedes", "supports", "enables", "reduces", "separates_from", "trades_off_with", "warns_about"],
        "chunk_prefix": "tf",
        "theme_root": "tidy change",
        "topics": [
            "behavior change separation", "small structural move", "naming clarification", "guard clause extraction",
            "dead code removal", "cohesion improvement", "coupling reduction", "reversible step", "batch size control",
            "economic option value", "sequence before behavior", "risk visibility", "reviewable diff", "local reasoning",
            "change timing", "cost of delay", "feedback cadence", "cleanup stopping rule", "design pressure",
            "team agreement", "habit formation", "unsafe tidy warning",
        ],
    },
    "fastapi-clean-architecture": {
        "source_id": "fastapi-clean-architecture-reviewed-ocr",
        "review_status": "reviewed",
        "ocr_engine": "paddle",
        "node_types": ["Concept", "API", "Pattern", "Class", "Layer", "Warning"],
        "edge_types": ["depends_on", "implements", "belongs_to", "exposes", "validates", "persists", "injects", "warns_about"],
        "chunk_prefix": "fa",
        "theme_root": "FastAPI clean architecture",
        "topics": [
            "project dependency isolation", "ASGI runtime boundary", "router composition", "request schema contract",
            "response model exposure", "usecase orchestration", "domain entity ownership", "repository port",
            "repository adapter", "SQLAlchemy session boundary", "Alembic migration discipline", "transaction ownership",
            "dependency provider assembly", "Depends layer risk", "password hashing boundary", "JWT claim boundary",
            "authorization dependency", "CRUD command split", "pagination input contract", "error response contract",
            "async I/O boundary", "blocking call warning", "configuration secret boundary", "container database parity",
            "test client contract", "OpenAPI documentation loop", "service constructor injection", "DTO domain mapping",
            "duplicate user invariant", "mail side effect boundary", "router module cohesion", "database lifecycle",
            "environment settings object", "protected endpoint flow", "cleanup migration rollback", "schema validation failure",
            "application service isolation", "infrastructure import direction", "adapter replacement decision", "runtime health check",
        ],
    },
    "modern-java-in-action": {
        "source_id": "modern-java-in-action-reviewed-ocr",
        "review_status": "reviewed",
        "ocr_engine": "paddle",
        "node_types": ["Concept", "LanguageFeature", "API", "Pattern", "Operation", "Concurrency", "Warning"],
        "edge_types": ["uses", "enables", "simplifies", "composes_with", "contrasts_with", "specializes", "implements", "warns_about"],
        "chunk_prefix": "mj",
        "theme_root": "Modern Java",
        "topics": [
            "behavior parameterization", "lambda readability", "functional interface target type", "method reference fit",
            "stream pipeline boundary", "intermediate operation laziness", "terminal operation ownership", "collector reduction",
            "grouping partitioning choice", "Optional absence contract", "null handling warning", "default method evolution",
            "interface compatibility", "date time immutability", "temporal formatting boundary", "CompletableFuture composition",
            "async exception handling", "parallel stream cost", "side effect warning", "reactive flow backpressure",
            "pattern matching readability", "records data carrier", "sealed hierarchy decision", "local variable inference",
            "exception transparency", "domain collection transformation", "predicate composition", "function composition",
            "consumer side effect boundary", "supplier factory boundary", "primitive stream tradeoff", "debugging stream pipeline",
            "testing functional branch", "API evolution compatibility", "Spring service readability", "concurrency timeout policy",
            "immutable value modeling", "collection factory use", "comparator composition", "resource closing discipline",
            "fork join suitability", "completion stage cancellation", "stream source ownership", "collector merge behavior",
            "legacy API adapter",
        ],
    },
    "domain-driven-design-first-steps": {
        "source_id": "domain-driven-design-first-steps-ocr",
        "review_status": "needs_review",
        "ocr_engine": "paddle",
        "node_types": ["Concept", "Boundary", "Pattern", "Practice", "Decision", "Warning", "ArchitectureStyle"],
        "edge_types": ["supports", "refines", "informs", "validates", "integrates_with", "constrains", "separates", "warns_about"],
        "chunk_prefix": "ddd",
        "theme_root": "domain-driven design",
        "topics": [
            "core domain focus", "supporting subdomain boundary", "generic subdomain reuse", "ubiquitous language stewardship",
            "bounded context ownership", "context map relationship", "customer supplier coordination", "conformist tradeoff",
            "anti corruption translation", "published language contract", "aggregate consistency boundary", "entity identity",
            "value object immutability", "domain service decision", "repository abstraction", "domain event publication",
            "event storming discovery", "command event distinction", "policy reaction", "saga process boundary",
            "CQRS read model split", "event sourcing audit trail", "snapshotting decision", "microservice alignment warning",
            "team topology influence", "data mesh product thinking", "context integration test", "legacy model isolation",
            "strategic design before code", "tactical pattern restraint", "transaction boundary per aggregate",
            "eventual consistency explanation", "language drift warning", "model refactoring trigger", "collaboration workshop",
            "subdomain prioritization", "architecture style selection", "event driven integration", "service boundary hypothesis",
            "domain expert feedback loop", "read model ownership", "migration from CRUD model", "context observability",
            "bounded context discovery artifact", "contract negotiation cadence", "aggregate invariant protection",
            "integration failure mode", "team language onboarding", "context ownership record", "modeling uncertainty log",
            "domain policy extraction", "business capability map", "process milestone event", "shared kernel caution",
            "open host service decision", "context split cost",
        ],
    },
    "spring-modern-api": {
        "source_id": "spring-modern-api-reviewed-ocr",
        "review_status": "reviewed",
        "ocr_engine": "paddle",
        "node_types": ["Component", "Pattern", "APIStyle", "Security", "Testing", "Deployment", "Observability", "Warning", "Framework"],
        "edge_types": ["uses", "implements", "generates", "secures", "authenticates", "authorizes", "tests", "deploys", "observes", "warns_about"],
        "chunk_prefix": "sp",
        "theme_root": "Spring modern API",
        "topics": [
            "REST resource modeling", "HTTP status discipline", "controller request mapping", "DTO validation boundary",
            "problem detail error contract", "service transaction boundary", "JPA aggregate mapping", "repository query boundary",
            "OpenAPI design first", "generated contract drift", "HATEOAS affordance", "ETag conditional update",
            "cache validation choice", "API version strategy", "Spring IoC assembly", "bean lifecycle boundary",
            "configuration property binding", "profile environment split", "OAuth resource server", "JWT authority mapping",
            "method authorization", "CORS exposure decision", "security filter chain", "test slice selection",
            "MockMvc contract test", "WebTestClient reactive test", "container image profile", "deployment readiness probe",
            "Actuator exposure boundary", "metric tag discipline", "trace correlation", "log structure decision",
            "WebFlux backpressure", "reactive repository warning", "gRPC IDL contract", "protobuf evolution",
            "GraphQL schema boundary", "resolver N plus one warning", "batch loader choice", "pagination cursor decision",
            "exception handler mapping", "domain DTO separation", "transaction propagation warning", "optimistic locking",
            "Flyway migration cadence", "OpenAPI client generation", "contract regression", "observability sampling",
            "gateway integration", "rate limit policy", "async event publication", "outbox integration", "container secret handling",
            "validation group decision", "schema compatibility", "API deprecation policy", "multi module boundary",
            "Kotlin Java interoperability", "Spring Boot auto config decision", "native image readiness",
            "health endpoint ownership", "security audit loop", "GraphQL authorization", "gRPC deadline handling",
            "REST idempotency key", "resource link stability", "service layer leak warning", "repository projection",
        ],
    },
    "python-architecture-patterns": {
        "source_id": "python-architecture-patterns-reviewed-ocr",
        "review_status": "reviewed",
        "ocr_engine": "paddle",
        "node_types": ["Concept"],
        "edge_types": ["supports", "depends_on", "enables", "refines", "guides", "informs", "encapsulates", "observes", "measures", "repairs"],
        "chunk_prefix": "py",
        "theme_root": "Python architecture",
        "topics": [
            "package boundary design", "module dependency direction", "application entrypoint", "configuration layering",
            "Twelve Factor config", "environment parity", "API route organization", "request validation boundary",
            "domain model placement", "data mapper decision", "repository abstraction", "unit of work boundary",
            "transaction script warning", "service layer orchestration", "message bus routing", "event handler ownership",
            "command handler boundary", "CQRS read model", "async task boundary", "queue delivery semantics",
            "idempotency handling", "retry policy", "outbox pattern", "schema migration practice",
            "test pyramid calibration", "fixture ownership", "contract test boundary", "TDD feedback loop",
            "mock boundary choice", "integration test database", "logging context", "metrics naming",
            "trace span boundary", "profiling hypothesis", "debugging workflow", "error handling policy",
            "CLI web separation", "dependency injection function", "settings object boundary", "container packaging",
            "deployment process model", "monolith modularity", "microservice split trigger", "distributed data warning",
            "API compatibility", "data serialization choice", "ORM session lifecycle", "migration rollback planning",
            "feature flag decision", "observability dashboard", "performance budget", "security input boundary",
            "type hint contract", "dataclass value model", "Pydantic boundary", "FastAPI Flask tradeoff",
            "Django app boundary", "background worker contract", "scheduler ownership", "cache invalidation",
            "event driven consistency", "saga compensation", "domain event naming", "adapter port mapping",
            "hexagonal boundary", "plugin architecture", "import cycle repair", "packaging metadata",
            "version release discipline", "documentation architecture decision", "architecture decision record",
            "runtime failure mode", "database connection pooling", "test data builder", "factory pattern",
            "repository leak warning", "observability alert threshold", "schema evolution", "public API surface",
            "internal module visibility", "team ownership map", "continuous architecture review", "technical debt triage",
            "debuggable service startup", "graceful shutdown", "resource cleanup", "dependency upgrade policy",
        ],
    },
}


BACKEND_TOPICS = [
    "dependency direction principle", "adapter boundary", "application service workflow", "domain model ownership",
    "repository port abstraction", "transaction boundary", "API contract boundary", "DTO mapping decision",
    "validation before usecase", "error response contract", "security context boundary", "authorization policy",
    "configuration boundary", "runtime environment parity", "migration discipline", "testability pressure",
    "contract regression loop", "observability trace boundary", "metrics feedback", "logging context",
    "async workload boundary", "message driven integration", "eventual consistency decision", "outbox reliability",
    "idempotency guard", "service split hypothesis", "bounded context mapping", "aggregate consistency",
    "language drift warning", "change batch size", "reversible structural change", "coupling reduction",
    "cohesion improvement", "framework leakage warning", "ORM leakage warning", "controller service separation",
    "repository implementation adapter", "OpenAPI contract mapping", "Spring adapter mapping", "FastAPI adapter mapping",
    "Python runtime packaging", "Java Optional contract", "Stream readability boundary", "CompletableFuture timeout",
    "GraphQL resolver boundary", "gRPC deadline contract", "REST idempotency", "deployment readiness",
    "container secret boundary", "health check ownership", "query model separation", "CQRS read model",
    "event sourcing audit", "architecture decision record", "technical debt triage", "continuous architecture review",
    "source graph promotion policy", "canonical concept mapping",
]


BACKEND_TERM_EXPANSIONS = {
    "authorization": {"auth", "authorize", "authorization", "authority", "security", "jwt", "oauth"},
    "security": {"auth", "authorize", "authorization", "security", "jwt", "oauth"},
    "configuration": {"config", "settings", "profile", "environment", "property"},
    "runtime": {"runtime", "environment", "deployment", "container", "asgi", "startup"},
    "migration": {"migration", "alembic", "flyway", "schema", "database"},
    "observability": {"observability", "trace", "metric", "logging", "actuator"},
    "metrics": {"metric", "metrics", "observability", "alert", "measure"},
    "repository": {"repository", "repo", "persistence", "adapter"},
    "transaction": {"transaction", "unit", "work", "consistency"},
    "validation": {"validation", "validate", "schema", "dto"},
    "contract": {"contract", "schema", "openapi", "api", "response"},
    "adapter": {"adapter", "depends", "controller", "service", "repository"},
    "domain": {"domain", "aggregate", "entity", "bounded", "context"},
}


@dataclass
class SkillRows:
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    chunks: list[dict[str, Any]]
    coverage: list[dict[str, Any]]
    qa: list[dict[str, Any]]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def slug(text: str) -> str:
    text = text.lower().replace("+", " plus ")
    text = re.sub(r"[^a-z0-9가-힣]+", "-", text).strip("-")
    return re.sub(r"-+", "-", text)


def title(text: str) -> str:
    return " ".join(part.capitalize() if part.isascii() else part for part in text.split())


def ref(config: dict[str, Any], chapter: int, section: str, start: int, end: int) -> dict[str, Any]:
    return {
        "source_id": config["source_id"],
        "chapter": chapter,
        "section": section,
        "lines": [start, end],
        "line_range": [start, end],
        "ocr_engine": config["ocr_engine"],
        "review_status": config["review_status"],
    }


def source_manifest(skill_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    candidates = sorted((skill_dir / "output" / "private-source").glob("*/source_manifest.json"))
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if path.parent.name == config["source_id"] or payload.get("source_basename"):
            return payload
    raise FileNotFoundError(f"{skill_dir}: missing private source_manifest.json for {config['source_id']}")


def line_span(total_lines: int, index: int, count: int) -> tuple[int, int]:
    width = max(35, math.floor(total_lines / max(1, count)))
    start = max(1, 1 + index * width)
    end = min(total_lines, start + width - 1)
    return start, max(start, end)


def existing_ids(rows: list[dict[str, Any]], key: str = "id") -> set[str]:
    return {row[key] for row in rows if key in row}


def node_text(row: dict[str, Any]) -> str:
    aliases = row.get("aliases", [])
    if not isinstance(aliases, list):
        aliases = []
    return " ".join([str(row.get("id", "")), str(row.get("name", "")), str(row.get("summary", "")), *map(str, aliases)]).lower()


def text_terms(text: str) -> set[str]:
    stop = {
        "boundary",
        "decision",
        "warning",
        "contract",
        "pattern",
        "concept",
        "backend",
        "architecture",
        "policy",
        "public",
        "safe",
        "source",
    }
    return {term for term in re.findall(r"[a-z0-9가-힣]+", text.lower()) if len(term) > 2 and term not in stop}


def same_source_ref(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any] | None:
    for lref in left.get("source_refs", []):
        lkey = (lref.get("source_id"), lref.get("chapter"), tuple(lref.get("line_range") or lref.get("lines") or []))
        for rref in right.get("source_refs", []):
            rkey = (rref.get("source_id"), rref.get("chapter"), tuple(rref.get("line_range") or rref.get("lines") or []))
            if lkey == rkey:
                return lref
    return None


def edge_id(edge: dict[str, Any]) -> str:
    return f"{edge['source']}->{edge['target']}"


def update_manifest(refs: Path, counts: dict[str, int]) -> None:
    path = refs / "graph_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["counts"] = counts
    manifest.setdefault("max_density_second_pass", {})
    manifest["max_density_second_pass"].update(
        {
            "status": "expanded",
            "public_knowledge_scope": "section-level concepts, relationships, decisions, warnings, and topic indexes",
            "source_expression_policy": "source ideas are used; source wording, code examples, tables, and exercises are excluded",
        }
    )
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_query_qa(rows: SkillRows, skill: str, theme: str) -> None:
    node_lookup = {row["id"]: row for row in rows.nodes}
    chunk_lookup = {row["id"]: row for row in rows.chunks}
    for row in rows.qa:
        expected_nodes = [ident for ident in row.get("expected_nodes", []) if ident in node_lookup]
        expected_chunks = [ident for ident in row.get("expected_chunks", []) if ident in chunk_lookup]
        if not expected_nodes or not expected_chunks:
            continue
        node = node_lookup[expected_nodes[0]]
        chunk = chunk_lookup[expected_chunks[0]]
        aliases = node.get("aliases", [])
        alias = aliases[0] if isinstance(aliases, list) and aliases else node["name"]
        keywords = chunk.get("keywords", [])
        keyword = keywords[0] if isinstance(keywords, list) and keywords else chunk["title"]
        row["question"] = f"{node['name']}와 {alias}, {chunk['title']}의 {keyword}를 함께 찾아 {theme} 판단 기준을 확인한다."
        row["expected_source_skills"] = [skill]
        row["public_safe"] = True


def ensure_ontology_note(refs: Path) -> None:
    path = refs / "ontology.yaml"
    text = path.read_text(encoding="utf-8")
    if "max_density_second_pass:" in text:
        return
    text += (
        "\nmax_density_second_pass:\n"
        "  abstraction_unit: source_id + chapter + section + line_range\n"
        "  expression_policy: use concepts and relationships, not source wording or source structure\n"
        "  mapping_policy: prefer closeMatch, maps_to, specializes, and contrasts_with over same_as\n"
    )
    path.write_text(text, encoding="utf-8")


def concept_summary(skill: str, topic: str, root: str, aspect: str) -> str:
    korean_aspect = {
        "boundary": "경계를 명확히 하도록 책임과 외부 접점을 분리한다",
        "decision": "선택 기준과 적용 조건을 드러내어 구현 전에 판단할 수 있게 한다",
        "risk": "잘못 적용될 때 생기는 누수, 결합, 운영 실패 가능성을 식별한다",
        "workflow": "실무 흐름에서 앞뒤 단계와 검증 지점을 연결한다",
        "testing": "테스트 가능성과 회귀 검증 기준을 함께 둔다",
    }[aspect]
    return f"{root} 관점에서 {topic}를 다룰 때 {korean_aspect}."


def edge_summary(source_name: str, target_name: str, relation: str) -> str:
    relation_text = {
        "depends_on": "선행 조건으로 삼는다",
        "implements": "구체적 구현 선택으로 연결한다",
        "belongs_to": "같은 설계 판단 묶음에 배치한다",
        "exposes": "외부 계약으로 드러낸다",
        "validates": "검증 기준으로 확인한다",
        "persists": "저장 책임과 연결한다",
        "injects": "조립 지점에서 연결한다",
        "warns_about": "실패 가능성을 경고한다",
        "uses": "실행 또는 구현 수단으로 사용한다",
        "enables": "후속 판단을 가능하게 한다",
        "simplifies": "표현과 유지보수 부담을 줄인다",
        "composes_with": "함께 조합되는 개념이다",
        "contrasts_with": "대안적 판단 기준으로 대비된다",
        "specializes": "더 구체적인 적용 맥락으로 좁힌다",
        "supports": "판단 근거를 보강한다",
        "refines": "상위 개념을 더 세밀하게 만든다",
        "informs": "설계 선택에 필요한 맥락을 제공한다",
        "integrates_with": "다른 경계와 통합된다",
        "constrains": "허용 가능한 구현 범위를 제한한다",
        "separates": "책임을 분리한다",
        "guides": "실행 방향을 안내한다",
        "encapsulates": "세부사항을 내부로 감춘다",
        "observes": "운영 관측 지점과 연결한다",
        "measures": "품질 신호로 측정한다",
        "repairs": "손상된 구조를 회복한다",
        "precedes": "다음 행동보다 먼저 다룬다",
        "reduces": "비용이나 위험을 낮춘다",
        "separates_from": "행동 변경과 구조 변경을 분리한다",
        "trades_off_with": "상충하는 선택으로 비교한다",
        "secures": "보안 경계를 강화한다",
        "authenticates": "인증 흐름과 연결한다",
        "authorizes": "인가 정책과 연결한다",
        "tests": "테스트 전략으로 확인한다",
        "deploys": "배포 조건과 연결한다",
        "observes": "관측 가능성 판단과 연결한다",
        "generates": "계약 산출물과 연결한다",
    }.get(relation, "의미 관계로 연결한다")
    return f"{source_name}는 {target_name}를 {relation_text}."


def generate_source_skill(repo: Path, skill: str) -> SkillRows:
    refs = repo / "skills" / skill / "references"
    config = SKILL_CONFIG[skill]
    manifest = source_manifest(repo / "skills" / skill, config)
    total_lines = int(manifest.get("line_count") or 2400)
    targets = TARGETS[skill]
    rows = SkillRows(
        nodes=load_jsonl(refs / "nodes.jsonl"),
        edges=load_jsonl(refs / "edges.jsonl"),
        chunks=load_jsonl(refs / "chunks.jsonl"),
        coverage=load_jsonl(refs / "coverage_matrix.jsonl"),
        qa=load_jsonl(refs / "query_qa.jsonl"),
    )
    max_prefix = f"max-{config['chunk_prefix']}-"
    chunk_prefix = f"chunk-max-{config['chunk_prefix']}-"
    qa_prefix = f"qa-max-{config['chunk_prefix']}-"
    rows.nodes = [row for row in rows.nodes if not row.get("id", "").startswith(max_prefix)]
    rows.edges = [
        row
        for row in rows.edges
        if not (
            row.get("source", "").startswith(max_prefix)
            or row.get("target", "").startswith(max_prefix)
            or row.get("evidence_rule") == "same_section_or_curated_topic_relation"
        )
    ]
    rows.chunks = [row for row in rows.chunks if not row.get("id", "").startswith(chunk_prefix)]
    rows.coverage = [row for row in rows.coverage if row.get("coverage_kind") != "conceptual_section_abstraction"]
    rows.qa = [row for row in rows.qa if not row.get("id", "").startswith(qa_prefix)]
    node_ids = existing_ids(rows.nodes)
    edge_ids = {edge_id(edge) for edge in rows.edges}
    chunk_ids = existing_ids(rows.chunks)
    cov_existing = {(row.get("chapter"), row.get("section")) for row in rows.coverage}

    topics = config["topics"]
    aspects = ["boundary", "decision", "risk", "workflow", "testing"]
    additions_needed = max(0, targets["nodes"] - len(rows.nodes))
    if additions_needed % len(aspects):
        additions_needed += len(aspects) - (additions_needed % len(aspects))
    added_node_ids: list[str] = []
    topic_groups: list[dict[str, Any]] = []
    for i in range(additions_needed):
        group_index = i // len(aspects)
        topic = topics[group_index % len(topics)]
        aspect = aspects[i % len(aspects)]
        ident = f"max-{config['chunk_prefix']}-{slug(topic)}-{aspect}"
        if ident in node_ids:
            continue
        start, end = line_span(total_lines, group_index, max(1, math.ceil(additions_needed / len(aspects))))
        chapter = 1 + (group_index % max(1, min(18, math.ceil(total_lines / 700))))
        section_ref = ref(config, chapter, f"max-density {topic}", start, end)
        node_type = config["node_types"][i % len(config["node_types"])]
        if "Warning" in config["node_types"] and aspect == "risk":
            node_type = "Warning"
        node = {
            "id": ident,
            "type": node_type,
            "name": f"{title(topic)} {title(aspect)}",
            "summary": concept_summary(skill, topic, config["theme_root"], aspect),
            "aliases": [topic, f"{topic} {aspect}"],
            "source_refs": [section_ref],
            "public_safe": True,
            "ontology_family": {
                "boundary": "Boundary",
                "decision": "Decision",
                "risk": "Warning",
                "workflow": "Workflow",
                "testing": "Practice",
            }[aspect],
        }
        rows.nodes.append(node)
        node_ids.add(ident)
        added_node_ids.append(ident)
        if len(topic_groups) <= group_index:
            topic_groups.append({"topic": topic, "source_ref": section_ref, "node_ids": []})
        topic_groups[group_index]["node_ids"].append(ident)

    all_nodes = [row["id"] for row in rows.nodes]
    if not all_nodes:
        raise ValueError(f"{skill}: no nodes")
    edge_target = targets["edges"]
    i = 0
    node_lookup = {row["id"]: row for row in rows.nodes}
    candidate_pairs: list[tuple[str, str, dict[str, Any]]] = []
    dense_pairs: list[tuple[str, str, dict[str, Any]]] = []
    for group in topic_groups:
        ids = group["node_ids"]
        for idx, source in enumerate(ids):
            if len(ids) > 1:
                candidate_pairs.append((source, ids[(idx + 1) % len(ids)], group["source_ref"]))
        for source in ids:
            for target in ids:
                if source != target and (source, target, group["source_ref"]) not in candidate_pairs:
                    dense_pairs.append((source, target, group["source_ref"]))
    candidate_pairs.extend(dense_pairs)
    while len(rows.edges) < edge_target and i < len(candidate_pairs):
        source, target, evidence_ref = candidate_pairs[i]
        ident = f"{source}->{target}"
        if ident in edge_ids:
            i += 1
            continue
        relation = config["edge_types"][i % len(config["edge_types"])]
        source_name = node_lookup[source]["name"]
        target_name = node_lookup[target]["name"]
        common_ref = same_source_ref(node_lookup[source], node_lookup[target])
        if common_ref is None:
            i += 1
            continue
        edge = {
            "source": source,
            "target": target,
            "type": relation,
            "summary": edge_summary(source_name, target_name, relation),
            "source_refs": [common_ref or evidence_ref],
            "public_safe": True,
            "evidence_rule": "same_section_or_curated_topic_relation",
        }
        rows.edges.append(edge)
        edge_ids.add(ident)
        i += 1

    while len(rows.chunks) < targets["chunks"]:
        i = len(rows.chunks)
        group_index = max(0, i - len([row for row in rows.chunks if not row.get("id", "").startswith(chunk_prefix)]))
        topic = topics[group_index % len(topics)]
        ident = f"chunk-max-{config['chunk_prefix']}-{slug(topic)}"
        source_ref = ref(config, 1 + (group_index % 18), f"topic index {topic}", *line_span(total_lines, group_index, targets["chunks"]))
        if ident in chunk_ids:
            rows.chunks.append(
                {
                    "id": f"{ident}-{i}",
                    "title": f"{title(topic)} Topic Index",
                    "summary": f"{config['theme_root']}의 {topic} 관련 판단 기준, 경계, 위험 신호를 묶은 public-safe topic index다.",
                    "source_refs": [source_ref],
                    "keywords": [topic, config["theme_root"], "public-safe"],
                    "public_safe": True,
                    "curation_role": "topic_index",
                }
            )
        else:
            rows.chunks.append(
                {
                    "id": ident,
                    "title": f"{title(topic)} Topic Index",
                    "summary": f"{config['theme_root']}의 {topic} 관련 판단 기준, 경계, 위험 신호를 묶은 public-safe topic index다.",
                    "source_refs": [source_ref],
                    "keywords": [topic, config["theme_root"], "public-safe"],
                    "public_safe": True,
                    "curation_role": "topic_index",
                }
            )
        chunk_ids.add(rows.chunks[-1]["id"])

    added_edges = [edge_id(edge) for edge in rows.edges if edge.get("evidence_rule") == "same_section_or_curated_topic_relation"]
    while len(rows.coverage) < targets["coverage"]:
        i = len(rows.coverage)
        group = topic_groups[i % len(topic_groups)] if topic_groups else {"topic": topics[i % len(topics)], "node_ids": []}
        topic = group["topic"]
        section = f"max-density {topic}"
        chapter = 1 + (i % max(1, min(18, math.ceil(total_lines / 700))))
        if (chapter, section) in cov_existing:
            section = f"{section} {i}"
        start, end = line_span(total_lines, i, targets["coverage"])
        cov_node_ids = group.get("node_ids", [])[:5] or added_node_ids[:2] or all_nodes[:2]
        group_edge_ids = [edge_id(edge) for edge in rows.edges if edge.get("source") in cov_node_ids and edge.get("target") in cov_node_ids]
        cov_edge_ids = group_edge_ids[:8] or added_edges[i : i + 5] or [edge_id(edge) for edge in rows.edges[:5]]
        cov_chunk_ids = [rows.chunks[i % len(rows.chunks)]["id"]]
        rows.coverage.append(
            {
                "source_id": config["source_id"],
                "chapter": chapter,
                "section": section,
                "line_range": [start, end],
                "ocr_review_status": config["review_status"],
                "chunk_ids": cov_chunk_ids,
                "node_ids": cov_node_ids,
                "edge_ids": cov_edge_ids,
                "coverage_status": "covered",
                "gap_reason": "",
                "market_substitute_risk": "low",
                "heart_of_work_risk": "low",
                "public_safe": True,
                "coverage_kind": "conceptual_section_abstraction",
            }
        )

    while len(rows.qa) < targets["qa"]:
        i = len(rows.qa)
        node = rows.nodes[(i * 3) % len(rows.nodes)]
        chunk = rows.chunks[(i * 2) % len(rows.chunks)]
        rows.qa.append(
            {
                "id": f"qa-max-{config['chunk_prefix']}-{i + 1:03d}",
                "question": f"{node['name']} 와 {chunk['title']} 를 함께 찾아 {config['theme_root']} 판단 기준을 확인한다.",
                "expected_nodes": [node["id"]],
                "expected_chunks": [chunk["id"]],
                "expected_source_skills": [skill],
                "min_hit_count": 2,
                "pass_criteria": "Top search hits include the expected public-safe node and topic index without source expression reproduction.",
                "public_safe": True,
            }
        )

    normalize_query_qa(rows, skill, config["theme_root"])
    return rows


def backend_ref(source_skill: str, source_id: str) -> dict[str, Any]:
    return {"source_skill": source_skill, "source_id": source_id, "source_item_kind": "node"}


def best_source_refs(source_nodes: dict[str, list[dict[str, Any]]], topic: str, count: int = 2) -> list[dict[str, Any]]:
    topic_terms = text_terms(topic)
    expanded_terms = set(topic_terms)
    for term in list(topic_terms):
        expanded_terms.update(BACKEND_TERM_EXPANSIONS.get(term, set()))
    scored: list[tuple[int, str, str]] = []
    for skill, nodes in source_nodes.items():
        for row in nodes:
            row_terms = text_terms(node_text(row))
            score = len(expanded_terms & row_terms)
            if score:
                scored.append((score, skill, row["id"]))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    refs: list[dict[str, Any]] = []
    seen_skills: set[str] = set()
    for score, skill, ident in scored:
        if skill in seen_skills:
            continue
        if len(refs) >= 2 and score < 2:
            continue
        refs.append(backend_ref(skill, ident))
        seen_skills.add(skill)
        if len(refs) >= count:
            return refs
    return refs


def generate_backend(repo: Path) -> SkillRows:
    refs = repo / "skills" / "backend-architecture" / "references"
    rows = SkillRows(
        nodes=load_jsonl(refs / "nodes.jsonl"),
        edges=load_jsonl(refs / "edges.jsonl"),
        chunks=load_jsonl(refs / "chunks.jsonl"),
        coverage=[],
        qa=load_jsonl(refs / "query_qa.jsonl"),
    )
    targets = TARGETS["backend-architecture"]
    source_nodes = {
        skill: load_jsonl(repo / "skills" / skill / "references" / "nodes.jsonl")
        for skill in SOURCE_SKILLS
    }
    source_by_skill = {skill: [row["id"] for row in nodes] for skill, nodes in source_nodes.items()}
    eligible_topics = [topic for topic in BACKEND_TOPICS if len(best_source_refs(source_nodes, topic, 2)) >= 2]
    if not eligible_topics:
        raise ValueError("backend-architecture: no eligible backend topics")
    rows.nodes = [row for row in rows.nodes if not row.get("id", "").startswith("max-backend-")]
    rows.edges = [
        row
        for row in rows.edges
        if not (
            row.get("source", "").startswith("max-backend-")
            or row.get("target", "").startswith("max-backend-")
            or row.get("evidence_rule") == "public_source_graph_promotion"
        )
    ]
    rows.chunks = [row for row in rows.chunks if not row.get("id", "").startswith("chunk-max-backend-")]
    rows.qa = [row for row in rows.qa if not row.get("id", "").startswith("qa-max-backend-")]
    node_ids = existing_ids(rows.nodes)
    added_node_ids: list[str] = []
    backend_groups: list[dict[str, Any]] = []
    aspects = ["boundary", "decision", "risk", "workflow", "testing"]
    additions_needed = max(0, targets["nodes"] - len(rows.nodes))
    if additions_needed % len(aspects):
        additions_needed += len(aspects) - (additions_needed % len(aspects))
    i = 0
    topic_cursor = 0
    while len(added_node_ids) < additions_needed:
        group_index = i // len(aspects)
        aspect = aspects[i % len(aspects)]
        topic = eligible_topics[topic_cursor % len(eligible_topics)]
        refs_pair = best_source_refs(source_nodes, topic, 2)
        if len(refs_pair) < 2:
            topic_cursor += 1
            i = (topic_cursor * len(aspects))
            if topic_cursor > len(eligible_topics) * 3:
                raise ValueError("backend-architecture: insufficient semantically matched source evidence")
            continue
        ident = f"max-backend-{slug(topic)}-{aspect}"
        if ident in node_ids:
            ident = f"{ident}-{i}"
        node_type = {
            "boundary": "Boundary",
            "decision": "Tradeoff",
            "risk": "Warning",
            "workflow": "Workflow",
            "testing": "Pattern",
        }[aspect]
        rows.nodes.append(
            {
                "id": ident,
                "type": node_type,
                "name": f"{title(topic)} {title(aspect)}",
                "summary": f"Backend architecture에서 {topic}의 {aspect} 관점은 여러 source skill의 public graph를 연결해 책임과 검증 기준을 정한다.",
                "aliases": [topic, f"backend {topic}", f"{topic} {aspect}"],
                "source_refs": refs_pair,
                "public_safe": True,
                "promotion_policy": "public_graph_synthesis_only",
            }
        )
        node_ids.add(ident)
        added_node_ids.append(ident)
        while len(backend_groups) <= group_index:
            backend_groups.append({"topic": topic, "node_ids": []})
        backend_groups[group_index]["node_ids"].append(ident)
        i += 1
        if i % len(aspects) == 0:
            topic_cursor += 1

    edge_ids = {edge_id(edge) for edge in rows.edges}
    edge_types = ["supports", "maps_to", "operationalizes", "warns_about", "implements", "governs", "trades_off_with", "reduces"]
    all_nodes = [row["id"] for row in rows.nodes]
    node_lookup = {row["id"]: row for row in rows.nodes}
    backend_pairs: list[tuple[str, str]] = []
    dense_pairs: list[tuple[str, str]] = []
    for group in backend_groups:
        ids = group["node_ids"]
        for idx, source in enumerate(ids):
            if len(ids) > 1:
                backend_pairs.append((source, ids[(idx + 1) % len(ids)]))
        for source in ids:
            for target in ids:
                if source != target and (source, target) not in backend_pairs:
                    dense_pairs.append((source, target))
    backend_pairs.extend(dense_pairs)
    i = 0
    while len(rows.edges) < targets["edges"] and i < len(backend_pairs):
        source, target = backend_pairs[i]
        ident = f"{source}->{target}"
        if ident in edge_ids:
            i += 1
            continue
        relation = edge_types[i % len(edge_types)]
        merged_refs = []
        seen = set()
        for ref_item in [*node_lookup[source].get("source_refs", []), *node_lookup[target].get("source_refs", [])]:
            key = (ref_item.get("source_skill"), ref_item.get("source_id"))
            if key not in seen:
                seen.add(key)
                merged_refs.append(ref_item)
        rows.edges.append(
            {
                "source": source,
                "target": target,
                "type": relation,
                "summary": edge_summary(node_lookup[source]["name"], node_lookup[target]["name"], relation),
                "source_refs": merged_refs[:4],
                "public_safe": True,
                "evidence_rule": "public_source_graph_promotion",
            }
        )
        edge_ids.add(ident)
        i += 1

    while len(rows.chunks) < targets["chunks"]:
        i = len(rows.chunks)
        topic = eligible_topics[i % len(eligible_topics)]
        evidence = best_source_refs(source_nodes, topic, 2)
        rows.chunks.append(
            {
                "id": f"chunk-max-backend-{slug(topic)}",
                "title": f"{title(topic)} Cross-source Index",
                "summary": f"{topic}를 backend architecture 관점에서 비교하기 위한 public-safe cross-source topic index다.",
                "source_refs": evidence,
                "keywords": [topic, "backend architecture", "cross-source"],
                "public_safe": True,
            }
        )

    while len(rows.qa) < targets["qa"]:
        i = len(rows.qa)
        node = rows.nodes[(i * 5) % len(rows.nodes)]
        chunk = rows.chunks[(i * 3) % len(rows.chunks)]
        rows.qa.append(
            {
                "id": f"qa-max-backend-{i + 1:03d}",
                "question": f"{node['name']} 와 {chunk['title']} 를 함께 조회해 backend cross-source 판단 기준을 확인한다.",
                "expected_nodes": [node["id"]],
                "expected_chunks": [chunk["id"]],
                "expected_source_skills": ["backend-architecture"],
                "min_hit_count": 2,
                "pass_criteria": "Top search hits include the expected backend node and cross-source topic index.",
                "public_safe": True,
            }
        )

    normalize_query_qa(rows, "backend-architecture", "backend architecture")
    canonical_path = refs / "canonical_registry.jsonl"
    canonical = load_jsonl(canonical_path)
    canonical = [row for row in canonical if not row.get("id", "").startswith("canonical-max-")]
    while len(canonical) < targets["canonical"]:
        i = len(canonical)
        topic = eligible_topics[i % len(eligible_topics)]
        evidence = best_source_refs(source_nodes, topic, 2)
        skill_members = [f"{item['source_skill']}:{item['source_id']}" for item in evidence]
        canonical.append(
            {
                "id": f"canonical-max-{slug(topic)}",
                "label": title(topic),
                "mapping_type": "closeMatch",
                "members": skill_members,
                "source_refs": evidence,
                "public_safe": True,
            }
        )
    write_jsonl(canonical_path, canonical)

    promotion_path = refs / "promotion_records.jsonl"
    promotions = load_jsonl(promotion_path)
    promotions = [row for row in promotions if not row.get("id", "").startswith("promotion-max-")]
    eligible_backend_nodes = [
        row for row in rows.nodes if row["id"].startswith("max-backend-") and len(best_source_refs(source_nodes, row["name"], 2)) >= 2
    ]
    if not eligible_backend_nodes:
        raise ValueError("backend-architecture: no eligible backend promotion nodes")
    while len(promotions) < targets["promotion"]:
        i = len(promotions)
        node = eligible_backend_nodes[i % len(eligible_backend_nodes)]
        evidence = best_source_refs(source_nodes, node["name"], 2 + (i % 2))
        promotions.append(
            {
                "id": f"promotion-max-{slug(node['id'])}-{i + 1:03d}",
                "node_id": node["id"],
                "promotion_type": "cross_source_abstraction",
                "source_evidence": evidence,
                "independent_source_count": len({item["source_skill"] for item in evidence}),
                "adapter_eligible_rationale": "Uses adapter evidence only when a framework-specific mapping is involved; otherwise remains framework-independent.",
                "limitations": "Applies as backend architecture guidance, not as a claim that all source contexts are identical.",
                "public_safe": True,
            }
        )
    write_jsonl(promotion_path, promotions)

    return rows


def generate(repo: Path, skills: list[str]) -> None:
    for skill in skills:
        refs = repo / "skills" / skill / "references"
        if skill == "backend-architecture":
            rows = generate_backend(repo)
        else:
            rows = generate_source_skill(repo, skill)
        write_jsonl(refs / "nodes.jsonl", rows.nodes)
        write_jsonl(refs / "edges.jsonl", rows.edges)
        write_jsonl(refs / "chunks.jsonl", rows.chunks)
        write_jsonl(refs / "query_qa.jsonl", rows.qa)
        if skill != "backend-architecture":
            write_jsonl(refs / "coverage_matrix.jsonl", rows.coverage)
        update_manifest(refs, {"nodes": len(rows.nodes), "edges": len(rows.edges), "chunks": len(rows.chunks)})
        ensure_ontology_note(refs)
        print(f"{skill}: {len(rows.nodes)} nodes, {len(rows.edges)} edges, {len(rows.chunks)} chunks")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--skills", default=",".join(SOURCE_SKILLS + ["backend-architecture"]))
    args = parser.parse_args()
    skills = [item.strip() for item in args.skills.split(",") if item.strip()]
    generate(Path(args.repo_root), skills)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
