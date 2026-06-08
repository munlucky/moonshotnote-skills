# moonshotnote-skills

Public Codex-compatible Agent Skills maintained under the `moonshotnote-skills` repository.

- `moonshotnote-ocr`: Korean-first screenshot and document-image OCR with PaddleOCR, optional PP-StructureV3/Surya fallbacks, and low-confidence visual review.
- `fastapi-clean-architecture`: public-safe FastAPI and clean architecture knowledge graph extracted from verified OCR notes.
- `text-knowledge-skill-builder`: reusable workflow for turning source text into public-safe knowledge-backed skills.
- `tidy-first`: public-safe Tidy First knowledge graph for small code tidying, behavior/structure separation, coupling, cohesion, reversibility, and options.
- `backend-architecture`: registry-driven public-safe backend architecture graph distilled from FastAPI, Tidy First, Spring Modern API, Python Architecture Patterns, DDD First Steps, and Modern Java backend code-quality skills, with verified FastAPI/Spring adapters and Java Optional/Stream/CompletableFuture boundary guidance.
- `modern-java-in-action`: public-safe Modern Java graph for lambdas, streams, collectors, Optional, default methods, date/time APIs, CompletableFuture, and Spring/backend code readability.
- `spring-modern-api`: public-safe Spring 6 and Spring Boot 3 modern API development graph for REST, OpenAPI, WebFlux, Security/JWT, deployment, observability, gRPC, and GraphQL.
- `python-architecture-patterns`: public-safe Python architecture graph for API design, data modeling, data layers, Twelve-Factor services, web server structure, event-driven systems, testing, packaging, observability, and continuous architecture.
- `domain-driven-design-first-steps`: public-safe Korean DDD study graph for subdomains, ubiquitous language, bounded contexts, context maps, tactical patterns, event sourcing, CQRS, event storming, microservices, event-driven architecture, and data mesh.
- `codebase-understanding`: lightweight codebase graph workflow for repository onboarding, architecture explanation, focused component analysis, and git diff impact review.
- `daily-webnovel-writing-knowledge`: public-safe Korean webnovel writing graph for planning, serialization strategy, episode structure, cliffhangers, reader metrics, submission, contracts, and sustainable completion habits.
- `teddynote-langchain-rag`: public-safe RAG and LangChain knowledge graph for document loading, splitting, embeddings, vector stores, retrievers, prompts, chains, evaluation, deployment, and troubleshooting.

## Install

From a published GitHub repository:

```powershell
npx skills add munlucky/moonshotnote-skills --skill moonshotnote-ocr -g -a codex -y
npx skills add munlucky/moonshotnote-skills --skill fastapi-clean-architecture -g -a codex -y
npx skills add munlucky/moonshotnote-skills --skill text-knowledge-skill-builder -g -a codex -y
npx skills add munlucky/moonshotnote-skills --skill tidy-first -g -a codex -y
npx skills add munlucky/moonshotnote-skills --skill backend-architecture -g -a codex -y
npx skills add munlucky/moonshotnote-skills --skill modern-java-in-action -g -a codex -y
npx skills add munlucky/moonshotnote-skills --skill spring-modern-api -g -a codex -y
npx skills add munlucky/moonshotnote-skills --skill python-architecture-patterns -g -a codex -y
npx skills add munlucky/moonshotnote-skills --skill domain-driven-design-first-steps -g -a codex -y
npx skills add munlucky/moonshotnote-skills --skill codebase-understanding -g -a codex -y
npx skills add munlucky/moonshotnote-skills --skill daily-webnovel-writing-knowledge -g -a codex -y
npx skills add munlucky/moonshotnote-skills --skill teddynote-langchain-rag -g -a codex -y
```

For local development from this checkout:

```powershell
npx skills add . --skill moonshotnote-ocr -g -a codex -y --copy
npx skills add . --skill fastapi-clean-architecture -g -a codex -y --copy
npx skills add . --skill text-knowledge-skill-builder -g -a codex -y --copy
npx skills add . --skill tidy-first -g -a codex -y --copy
npx skills add . --skill backend-architecture -g -a codex -y --copy
npx skills add . --skill modern-java-in-action -g -a codex -y --copy
npx skills add . --skill spring-modern-api -g -a codex -y --copy
npx skills add . --skill python-architecture-patterns -g -a codex -y --copy
npx skills add . --skill domain-driven-design-first-steps -g -a codex -y --copy
npx skills add . --skill codebase-understanding -g -a codex -y --copy
npx skills add . --skill daily-webnovel-writing-knowledge -g -a codex -y --copy
npx skills add . --skill teddynote-langchain-rag -g -a codex -y --copy
```

## moonshotnote-ocr Setup

The skill intentionally does not bundle OCR models or heavy Python dependencies. Install them into a shared Moonshot Relay runtime so Codex and Claude account-root copies can reuse the same OCR environment.

Supported local setup targets:

- Windows x64 with Python 3.10, 3.11, or 3.12
- macOS Apple Silicon arm64 with Python 3.10, 3.11, or 3.12
- Linux x64 with Python 3.10, 3.11, or 3.12

macOS Intel x86_64 is not supported by the pinned `paddlepaddle==3.2.2` runtime because the matching macOS x86_64 wheel is not published.

After `npx skills add`:

```powershell
cd $HOME\.codex\skills\moonshotnote-ocr
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

Default setup installs the PaddleOCR core runtime only. Install optional table/layout dependencies only when needed:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -InstallStructure
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -InstallSurya
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -InstallAll
```

On macOS Apple Silicon or Linux:

```bash
cd ~/.codex/skills/moonshotnote-ocr
bash scripts/setup.sh
```

Optional dependencies can be requested explicitly:

```bash
bash scripts/setup.sh --with-structure
bash scripts/setup.sh --with-surya
bash scripts/setup.sh --with-all
```

By default, setup creates `%MOONSHOT_RELAY_HOME%\runtimes\moonshotnote-ocr-py312`, or `%USERPROFILE%\.moonshot-relay\runtimes\moonshotnote-ocr-py312` when `MOONSHOT_RELAY_HOME` is unset. Set `MOONSHOTNOTE_OCR_RUNTIME` or pass `-RuntimePath` only when a custom shared runtime location is required.

Do not install or set up these skills under `~/.agents/skills`; use account roots such as `~/.codex/skills` or `~/.claude/skills`.

From a repository checkout:

```powershell
cd skills\moonshotnote-ocr
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

On macOS Apple Silicon or Linux from a repository checkout:

```bash
cd skills/moonshotnote-ocr
bash scripts/setup.sh
```

The setup scripts create or update the shared runtime, install pinned PaddlePaddle/PaddleOCR core dependencies from binary wheels, then run `scripts/doctor.py`. PP-StructureV3 and Surya are optional installs because their transitive wheels are heavier and more platform-sensitive, especially on macOS. The scripts reject unsupported Python or CPU combinations because OCR dependencies otherwise fall back to fragile local source builds. If `uv` is available and no compatible system Python exists, setup installs a uv-managed Python runtime for the runtime. `doctor.py` reports PP-StructureV3 and Surya as optional capabilities and shows whether it is running inside the shared runtime.

## moonshotnote-ocr Usage

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts\ocr_image.py C:\path\to\screenshot.png --engine paddle --lang korean
```

macOS/Linux:

```bash
OCR_PYTHON="${MOONSHOT_RELAY_HOME:-$HOME/.moonshot-relay}/runtimes/moonshotnote-ocr-py312/bin/python"
"$OCR_PYTHON" scripts/ocr_image.py ~/Desktop/screenshot.png --engine paddle --lang korean
```

Batch OCR cropped screenshots:

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts\ocr_image.py C:\path\to\captures --pattern *-crop.png --engine paddle --lang korean --summary
```

Automatic engine selection:

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts\ocr_image.py C:\path\to\page.png --engine auto --lang korean
```

Ebook page routing:

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts\ocr_image.py C:\path\to\ebook-page.png --engine auto --page-mode auto --lang korean --json
```

PaddleOCR-only mode avoids Surya runtime use:

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts\ocr_image.py C:\path\to\page.png --engine paddle --page-mode auto --lang korean
```

PP-StructureV3 can be requested only when `scripts\doctor.py` reports `optional_capabilities.pp_structure.available=true`:

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts\ocr_image.py C:\path\to\table.png --engine pp-structure --page-mode table --lang korean --json
```

Outputs:

```text
<input-dir>/ocr-output/<engine>/
  screenshot.paddle.txt
```

Default output is `.txt` only. Use `--json` for structured OCR evidence, `--md` for a review report, `--summary` for `batch_summary.json`, or `--all` to write every output. JSON keeps the legacy `engine`, `input`, `text`, `items`, `warnings`, and `low_confidence` keys and may add `requested_engine`, `fallback_used`, `fallback_reason`, `page_type`, `page_type_confidence`, `runtime_metadata`, and `structured`.

Low-confidence visual review:

```powershell
$ocrPython = "$HOME\.moonshot-relay\runtimes\moonshotnote-ocr-py312\Scripts\python.exe"
& $ocrPython scripts\ocr_image.py C:\path\to\screenshot.png --engine paddle --lang korean --json
& $ocrPython scripts\review_low_confidence.py C:\path\to\ocr-output\paddle --threshold 0.75
```

The review script creates crop images, contact sheets, `low_confidence_manifest.json`, and `low_confidence_review.md`. Do not treat OCR as fully verified while manifest items remain `needs_review`.

Batch behavior:

- Continues processing later images when one image fails.
- Returns a non-zero exit code if any item failed.
- Use `--fail-fast` when the first failure should stop the batch immediately.

## Engine Policy

- Use PaddleOCR first for normal screenshots, UI captures, signs, receipts, and Korean or mixed Korean-English images.
- Use `--page-mode auto` for ebook captures so PaddleOCR boxes classify plain text, tables, multi-column pages, layout-heavy pages, or unknown pages.
- Use optional PP-StructureV3 for table/layout parsing only when `doctor.py` reports it is available.
- Use Surya for document pages where reading order, formulas, complex layout, or markdown reconstruction matter.
- Use `--engine paddle` to keep execution on PaddleOCR and avoid Surya runtime use.
- Use a PDF skill for PDF extraction and page rendering. This skill only handles image inputs or already-rendered scanned pages.

## fastapi-clean-architecture Usage

The FastAPI skill does not bundle the full OCR text. It ships a public-safe graph and helper scripts:

```powershell
py -3 skills\fastapi-clean-architecture\scripts\query_graph.py --q "FastAPI Depends 의존성 주입" --json
py -3 skills\fastapi-clean-architecture\scripts\expand_context.py --q "회원가입 유스케이스" --out skills\fastapi-clean-architecture\output\source-pack.md
py -3 skills\fastapi-clean-architecture\scripts\validate_graph.py skills\fastapi-clean-architecture\references
```

For local private source metadata, run `prepare_private_source.py` with the reviewed OCR text and low-confidence review closeout. Its outputs are written under `skills/fastapi-clean-architecture/output/private-source/`, which is ignored by git.

## text-knowledge-skill-builder Usage

Use this skill when turning long source text into a reusable Skill:

```powershell
py -3 skills\text-knowledge-skill-builder\scripts\chunk_source_text.py --source <source.txt> --out-dir skills\<target-skill>\output\private-source
py -3 skills\text-knowledge-skill-builder\scripts\lint_knowledge_pack.py skills\<target-skill>\references
py -3 skills\text-knowledge-skill-builder\scripts\audit_public_safety.py skills\<target-skill>
```

The workflow is `text -> knowledge -> skill`: private source chunks stay ignored under `output/`, while public Skill references contain summaries, graph relations, provenance, and validation scripts.

## daily-webnovel-writing-knowledge Usage

The Daily Webnovel Writing Knowledge skill ships a public-safe graph and helper query script:

```powershell
py -3 skills\daily-webnovel-writing-knowledge-skill\scripts\query_knowledge.py "연재 전략"
py -3 skills\daily-webnovel-writing-knowledge-skill\scripts\query_knowledge.py "클리프행어"
py -3 skills\text-knowledge-skill-builder\scripts\lint_knowledge_pack.py skills\daily-webnovel-writing-knowledge-skill\references
```

The tracked graph contains only summaries, source references, and relationships.

## teddynote-langchain-rag Usage

The TeddyNote LangChain RAG skill ships a public-safe graph and helper query script:

```powershell
py -3 skills\teddynote-langchain-rag\scripts\query_knowledge.py "retriever"
py -3 skills\teddynote-langchain-rag\scripts\query_knowledge.py "chunking"
py -3 skills\text-knowledge-skill-builder\scripts\lint_knowledge_pack.py skills\teddynote-langchain-rag\references
```

The tracked graph contains only summaries, source references, and relationships.

## tidy-first Usage

The Tidy First skill does not bundle the full OCR text. It ships a public-safe graph and helper scripts:

```powershell
py -3 skills\tidy-first\scripts\query_graph.py --q "behavior change와 tidying 분리" --json
py -3 skills\tidy-first\scripts\query_graph.py --q "coupling cohesion reversible change" --json
py -3 skills\tidy-first\scripts\expand_context.py --q "guard clause dead code symmetry" --out skills\tidy-first\output\source-pack.md
py -3 skills\tidy-first\scripts\validate_graph.py skills\tidy-first\references
```

Private OCR-derived source chunks stay under `skills/tidy-first/output/private-source/`, which is ignored by git. The tracked graph contains only summaries, source references, and relationships.

## backend-architecture Usage

The Backend Architecture skill is a registry-driven meta skill. It distills framework-independent principles from public-safe FastAPI, Tidy First, Spring Modern API, Python Architecture Patterns, DDD First Steps, and Modern Java graphs. It includes verified FastAPI and Spring adapters plus backend data, runtime, operations, quality-loop, domain-modeling, and Java Optional/Stream/CompletableFuture boundary guidance:

```powershell
py -3 skills\backend-architecture\scripts\query_graph.py --q "service layer repository dependency inversion" --json
py -3 skills\backend-architecture\scripts\query_graph.py --q "FastAPI Depends layer leak" --json
py -3 skills\backend-architecture\scripts\query_graph.py --q "Spring @RestController @Service @Repository JPA" --json
py -3 skills\backend-architecture\scripts\query_graph.py --q "Spring Optional Stream service layer side effect" --json
py -3 skills\backend-architecture\scripts\query_graph.py --q "WebFlux Mono Flux layer leak" --json
py -3 skills\backend-architecture\scripts\query_graph.py --q "event-driven queue monolith microservice tradeoff" --json
py -3 skills\backend-architecture\scripts\query_graph.py --q "observability metrics profiling continuous architecture" --json
py -3 skills\backend-architecture\scripts\query_graph.py --q "bounded context aggregate repository domain event" --json
py -3 skills\backend-architecture\scripts\query_graph.py --q "event sourcing CQRS event storming data mesh" --json
py -3 skills\backend-architecture\scripts\expand_context.py --q "coupling cohesion change cost" --out skills\backend-architecture\output\source-pack.md
py -3 skills\backend-architecture\scripts\build_from_source_skills.py --check
py -3 skills\backend-architecture\scripts\validate_graph.py skills\backend-architecture\references
```

Other framework adapters are extension points only until backed by project evidence or a public-safe source graph.

## spring-modern-api Usage

The Spring Modern API skill does not bundle the full OCR text. It ships a public-safe graph and helper scripts:

```powershell
py -3 skills\spring-modern-api\scripts\query_graph.py --q "Spring Security JWT refresh token" --json
py -3 skills\spring-modern-api\scripts\query_graph.py --q "OpenAPI design-first codegen" --json
py -3 skills\spring-modern-api\scripts\expand_context.py --q "WebFlux Mono Flux R2DBC" --out skills\spring-modern-api\output\source-pack.md
py -3 skills\spring-modern-api\scripts\validate_graph.py skills\spring-modern-api\references
```

Private OCR-derived source chunks stay under `skills/spring-modern-api/output/private-source/`, which is ignored by git. The tracked graph contains only summaries, source references, and relationships.

## python-architecture-patterns Usage

The Python Architecture Patterns skill does not bundle the full OCR text. It ships a public-safe graph and a lightweight query helper:

```powershell
py -3 skills\python-architecture-patterns\scripts\query_knowledge.py architecture --limit 5
py -3 skills\python-architecture-patterns\scripts\query_knowledge.py "event driven" --limit 5
py -3 skills\text-knowledge-skill-builder\scripts\lint_knowledge_pack.py skills\python-architecture-patterns\references
py -3 skills\text-knowledge-skill-builder\scripts\audit_public_safety.py skills\python-architecture-patterns
```

Private OCR-derived source chunks stay under `skills/python-architecture-patterns/output/private-source/`, which is ignored by git. The tracked graph contains only summaries, source references, and relationships.

## domain-driven-design-first-steps Usage

The Domain-Driven Design First Steps skill does not bundle the full OCR text. It ships a public-safe graph and helper scripts:

```powershell
py -3 skills\domain-driven-design-first-steps\scripts\query_graph.py --q "바운디드 컨텍스트" --limit 5
py -3 skills\domain-driven-design-first-steps\scripts\query_graph.py --q "이벤트 소싱 CQRS" --limit 5
py -3 skills\domain-driven-design-first-steps\scripts\expand_context.py --node bounded-context
py -3 skills\text-knowledge-skill-builder\scripts\lint_knowledge_pack.py skills\domain-driven-design-first-steps\references
py -3 skills\text-knowledge-skill-builder\scripts\audit_public_safety.py skills\domain-driven-design-first-steps
```

Private OCR-derived source chunks stay under `skills/domain-driven-design-first-steps/output/private-source/`, which is ignored by git. The tracked graph contains only summaries, source references, and relationships. The current source quality gate records `321/321` OCR pages processed and `452` low-confidence items still requiring visual review before exact source wording is trusted.

## Public-Safe OCR Graph Validation

Programming OCR-derived skills include coverage and query QA fixtures so concept coverage is checked without publishing raw source text:

```powershell
py -3 tools\run_public_graph_gates.py --skills tidy-first,fastapi-clean-architecture,modern-java-in-action,domain-driven-design-first-steps,spring-modern-api,python-architecture-patterns,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
py -3 tools\run_public_graph_gates.py --profile local-full --skills tidy-first,fastapi-clean-architecture,modern-java-in-action,domain-driven-design-first-steps,spring-modern-api,python-architecture-patterns,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill --run-id latest
py -3 tools\validate_coverage_matrix.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill --min-coverage 0.95
py -3 tools\validate_query_qa.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill --top-n 20
py -3 tools\validate_backend_meta_artifacts.py --repo-root .
py -3 tools\validate_edge_evidence.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
py -3 tools\validate_transform_trace.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
py -3 tools\validate_forbidden_material.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
py -3 tools\validate_substitution_risk.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
py -3 tools\validate_no_manifest_only_generation.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill --run-id latest
py -3 tools\validate_chunk_grounding.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill --run-id latest
py -3 tools\audit_public_verbatim.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill --max-verbatim-words 25 --max-char-shingle 80 --fail-on-source-code-match --fail-on-table-or-exercise-match
py -3 tools\validate_id_stability.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
py -3 tools\validate_source_ref_density.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
py -3 tools\validate_query_diversity.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
```

`tools\extract_chunk_grounded_candidates.py` reads ignored `source_chunks.jsonl` text and writes private semantic candidate ledgers under ignored `output/extraction-candidates/`. `tools\apply_chunk_grounded_traces.py` then attaches public-safe `transform_trace` metadata to references without copying OCR text. `tools\generate_max_density_public_graph.py` remains a bootstrap expansion utility, not the authoritative chunk-content extractor.

## codebase-understanding Usage

The Codebase Understanding skill creates a lightweight local graph for repo onboarding, focused explanations, and diff impact review.

Normal Codex usage is skill-first. Ask Codex to use the skill; do not treat the Python commands below as commands the user must memorize:

```text
$codebase-understanding 전체 온보딩 해줘
$codebase-understanding 인증 흐름이 어떻게 구성돼?
$codebase-understanding src\auth.ts:login 설명해줘
$codebase-understanding src\auth.ts 변경 영향 분석해줘
$codebase-understanding 학습용 리딩 가이드 만들어줘
$codebase-understanding 대시보드 열어줘
```

When the skill is invoked without a path, Codex should use the current session's project/workspace root as the target repository. Codex should create or reuse `.codebase-understanding/codebase-map.json`, choose the right consumer mode (`onboard`, `chat`, `explain`, `diff`, `study`, or `dashboard`), run the bundled scripts itself, and verify final claims against source files.

The skill name is `codebase-understanding` because it is the individual capability. `moonshotnote-skills` is the repository that distributes this and other skills.

By default the scanner climbs from a supplied subdirectory to the detected project root, so repository manifests and `tsconfig.json` / `jsconfig.json` resolver settings are available. Add `--no-root-discovery` only when you intentionally want a narrow subdirectory-only graph.

Manual CLI fallback:

```powershell
py -3 C:\Users\moon\.codex\skills\codebase-understanding\scripts\understand_codebase.py
```

```bash
python3 ~/.codex/skills/codebase-understanding/scripts/understand_codebase.py
```

Run the manual fallback from the repository you want to analyze. This scans the project, saves `.codebase-understanding/codebase-map.json`, writes semantic review packs and heuristic annotations under `.codebase-understanding/`, writes `.codebase-understanding/diff-overlay.json` when git changed files exist, then opens the dashboard. Use `--no-dashboard` for CI or headless runs.

Consumer modes:

```powershell
py -3 skills\codebase-understanding\scripts\understand_codebase.py chat . "How is this repo organized?"
py -3 skills\codebase-understanding\scripts\understand_codebase.py diff . --changed-file src\example.py
py -3 skills\codebase-understanding\scripts\understand_codebase.py explain . README.md
py -3 skills\codebase-understanding\scripts\understand_codebase.py onboard .
py -3 skills\codebase-understanding\scripts\understand_codebase.py study .
py -3 skills\codebase-understanding\scripts\understand_codebase.py semantic .
py -3 skills\codebase-understanding\scripts\understand_codebase.py dashboard .
```

```bash
python3 skills/codebase-understanding/scripts/understand_codebase.py chat . "How is this repo organized?"
python3 skills/codebase-understanding/scripts/understand_codebase.py diff . --changed-file src/example.py
python3 skills/codebase-understanding/scripts/understand_codebase.py explain . README.md
python3 skills/codebase-understanding/scripts/understand_codebase.py onboard .
python3 skills/codebase-understanding/scripts/understand_codebase.py study .
python3 skills/codebase-understanding/scripts/understand_codebase.py semantic .
python3 skills/codebase-understanding/scripts/understand_codebase.py dashboard .
```

Lower-level scripts remain available for narrow automation.

Windows:

```powershell
py -3 skills\codebase-understanding\scripts\scan_codebase.py . --out .codebase-understanding\codebase-map.json
py -3 skills\codebase-understanding\scripts\validate_graph.py .codebase-understanding\codebase-map.json
py -3 skills\codebase-understanding\scripts\query_graph.py .codebase-understanding\codebase-map.json --q "repository service"
py -3 skills\codebase-understanding\scripts\explain_graph.py .codebase-understanding\codebase-map.json README.md --root .
py -3 skills\codebase-understanding\scripts\build_chat_prompt.py .codebase-understanding\codebase-map.json --q "How is this repo organized?"
py -3 skills\codebase-understanding\scripts\semantic_graph.py run .codebase-understanding\codebase-map.json --root . --packs-dir .codebase-understanding\semantic-packs --annotations-out .codebase-understanding\semantic-annotations.json --out .codebase-understanding\codebase-map.json
py -3 skills\codebase-understanding\scripts\query_graph.py .codebase-understanding\codebase-map.json --changed-file src\example.py
py -3 skills\codebase-understanding\scripts\write_diff_overlay.py .codebase-understanding\codebase-map.json --changed-file src\example.py --out .codebase-understanding\diff-overlay.json
py -3 skills\codebase-understanding\scripts\serve_dashboard.py .codebase-understanding\codebase-map.json --diff-overlay .codebase-understanding\diff-overlay.json
```

macOS/Linux:

```bash
python3 skills/codebase-understanding/scripts/scan_codebase.py . --out .codebase-understanding/codebase-map.json
python3 skills/codebase-understanding/scripts/validate_graph.py .codebase-understanding/codebase-map.json
python3 skills/codebase-understanding/scripts/query_graph.py .codebase-understanding/codebase-map.json --q "repository service"
python3 skills/codebase-understanding/scripts/explain_graph.py .codebase-understanding/codebase-map.json README.md --root .
python3 skills/codebase-understanding/scripts/build_chat_prompt.py .codebase-understanding/codebase-map.json --q "How is this repo organized?"
python3 skills/codebase-understanding/scripts/semantic_graph.py run .codebase-understanding/codebase-map.json --root . --packs-dir .codebase-understanding/semantic-packs --annotations-out .codebase-understanding/semantic-annotations.json --out .codebase-understanding/codebase-map.json
python3 skills/codebase-understanding/scripts/query_graph.py .codebase-understanding/codebase-map.json --changed-file src/example.py
python3 skills/codebase-understanding/scripts/write_diff_overlay.py .codebase-understanding/codebase-map.json --changed-file src/example.py --out .codebase-understanding/diff-overlay.json
python3 skills/codebase-understanding/scripts/serve_dashboard.py .codebase-understanding/codebase-map.json --diff-overlay .codebase-understanding/diff-overlay.json
```

Generated graph output stays under `.codebase-understanding/` and should not be committed unless a user explicitly wants a durable repo map.
The dashboard includes preset searches for entry points, prompt flow, commands, tools, permissions, messages, config, and tests. Selecting a node shows responsibility, evidence, risk hints, source excerpts, relationships, and copyable follow-up commands; use it to narrow the graph before reading source.

## Dependency Licenses

The skill scripts are MIT licensed. Runtime OCR dependencies keep their own licenses. In particular, `surya-ocr` is GPL-3.0-or-later, so review dependency licensing before bundling this skill into proprietary redistributed products. See `THIRD_PARTY_NOTICES.md`.

## Validation

On Windows, set UTF-8 mode before running `quick_validate.py` because some skills contain Korean text:

```powershell
$env:PYTHONUTF8 = "1"
```

```powershell
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\moonshotnote-ocr
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\fastapi-clean-architecture
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\text-knowledge-skill-builder
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\tidy-first
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\backend-architecture
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\modern-java-in-action
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\spring-modern-api
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\python-architecture-patterns
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\domain-driven-design-first-steps
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\codebase-understanding
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\daily-webnovel-writing-knowledge-skill
py -3.10 C:\Users\moon\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills\teddynote-langchain-rag
py -3 skills\fastapi-clean-architecture\scripts\validate_graph.py skills\fastapi-clean-architecture\references
py -3 skills\text-knowledge-skill-builder\scripts\lint_knowledge_pack.py skills\fastapi-clean-architecture\references
py -3 skills\text-knowledge-skill-builder\scripts\audit_public_safety.py skills\fastapi-clean-architecture
py -3 skills\tidy-first\scripts\validate_graph.py skills\tidy-first\references
py -3 skills\text-knowledge-skill-builder\scripts\lint_knowledge_pack.py skills\tidy-first\references
py -3 skills\text-knowledge-skill-builder\scripts\audit_public_safety.py skills\tidy-first
py -3 skills\backend-architecture\scripts\validate_graph.py skills\backend-architecture\references
py -3 skills\text-knowledge-skill-builder\scripts\lint_knowledge_pack.py skills\backend-architecture\references
py -3 skills\text-knowledge-skill-builder\scripts\audit_public_safety.py skills\backend-architecture
py -3 skills\spring-modern-api\scripts\validate_graph.py skills\spring-modern-api\references
py -3 skills\text-knowledge-skill-builder\scripts\lint_knowledge_pack.py skills\spring-modern-api\references
py -3 skills\text-knowledge-skill-builder\scripts\audit_public_safety.py skills\spring-modern-api
py -3 skills\text-knowledge-skill-builder\scripts\lint_knowledge_pack.py skills\python-architecture-patterns\references
py -3 skills\text-knowledge-skill-builder\scripts\audit_public_safety.py skills\python-architecture-patterns
py -3 skills\text-knowledge-skill-builder\scripts\lint_knowledge_pack.py skills\domain-driven-design-first-steps\references
py -3 skills\text-knowledge-skill-builder\scripts\audit_public_safety.py skills\domain-driven-design-first-steps
py -3 tools\run_public_graph_gates.py --skills tidy-first,fastapi-clean-architecture,modern-java-in-action,domain-driven-design-first-steps,spring-modern-api,python-architecture-patterns,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
py -3 tools\run_public_graph_gates.py --profile local-full --skills tidy-first,fastapi-clean-architecture,modern-java-in-action,domain-driven-design-first-steps,spring-modern-api,python-architecture-patterns,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill --run-id latest
py -3 tools\validate_coverage_matrix.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill --min-coverage 0.95
py -3 tools\validate_query_qa.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill --top-n 20
py -3 tools\validate_backend_meta_artifacts.py --repo-root .
py -3 tools\validate_edge_evidence.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
py -3 tools\validate_transform_trace.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
py -3 tools\validate_forbidden_material.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
py -3 tools\validate_substitution_risk.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
py -3 tools\validate_no_manifest_only_generation.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill --run-id latest
py -3 tools\validate_chunk_grounding.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill --run-id latest
py -3 tools\audit_public_verbatim.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill --max-verbatim-words 25 --max-char-shingle 80 --fail-on-source-code-match --fail-on-table-or-exercise-match
py -3 tools\validate_id_stability.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
py -3 tools\validate_source_ref_density.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
py -3 tools\validate_query_diversity.py --skills fastapi-clean-architecture,spring-modern-api,python-architecture-patterns,domain-driven-design-first-steps,modern-java-in-action,tidy-first,backend-architecture,teddynote-langchain-rag,daily-webnovel-writing-knowledge-skill
py -3 skills\text-knowledge-skill-builder\scripts\lint_knowledge_pack.py skills\teddynote-langchain-rag\references
py -3 skills\text-knowledge-skill-builder\scripts\audit_public_safety.py skills\teddynote-langchain-rag
py -3 skills\text-knowledge-skill-builder\scripts\lint_knowledge_pack.py skills\daily-webnovel-writing-knowledge-skill\references
py -3 skills\text-knowledge-skill-builder\scripts\audit_public_safety.py skills\daily-webnovel-writing-knowledge-skill
py -3 skills\codebase-understanding\scripts\scan_codebase.py . --out .codebase-understanding\codebase-map.json
py -3 skills\codebase-understanding\scripts\validate_graph.py .codebase-understanding\codebase-map.json
py -3 skills\codebase-understanding\scripts\explain_graph.py .codebase-understanding\codebase-map.json README.md --root .
py -3 skills\codebase-understanding\scripts\build_chat_prompt.py .codebase-understanding\codebase-map.json --q "backend architecture"
py -3 skills\codebase-understanding\scripts\semantic_graph.py run .codebase-understanding\codebase-map.json --root . --packs-dir .codebase-understanding\semantic-packs --annotations-out .codebase-understanding\semantic-annotations.json --out .codebase-understanding\codebase-map.json
py -3 skills\codebase-understanding\scripts\write_diff_overlay.py .codebase-understanding\codebase-map.json --changed-file README.md --out .codebase-understanding\diff-overlay.json
py -3 skills\codebase-understanding\scripts\understand_codebase.py analyze . --no-dashboard
py -3 skills\codebase-understanding\scripts\understand_codebase.py chat . "backend architecture" --graph .codebase-understanding\codebase-map.json
py -3 skills\codebase-understanding\scripts\understand_codebase.py explain . README.md --graph .codebase-understanding\codebase-map.json
py -3 skills\codebase-understanding\scripts\understand_codebase.py diff . --graph .codebase-understanding\codebase-map.json --changed-file README.md
py -3 skills\codebase-understanding\scripts\understand_codebase.py onboard . --graph .codebase-understanding\codebase-map.json
py -3 skills\codebase-understanding\scripts\understand_codebase.py study . --graph .codebase-understanding\codebase-map.json --limit 20
py -3 skills\codebase-understanding\scripts\understand_codebase.py semantic . --graph .codebase-understanding\codebase-map.json
npx skills add . --skill moonshotnote-ocr -g -a codex -y --copy
npx skills add . --skill fastapi-clean-architecture -g -a codex -y --copy
npx skills add . --skill text-knowledge-skill-builder -g -a codex -y --copy
npx skills add . --skill tidy-first -g -a codex -y --copy
npx skills add . --skill backend-architecture -g -a codex -y --copy
npx skills add . --skill modern-java-in-action -g -a codex -y --copy
npx skills add . --skill spring-modern-api -g -a codex -y --copy
npx skills add . --skill python-architecture-patterns -g -a codex -y --copy
npx skills add . --skill domain-driven-design-first-steps -g -a codex -y --copy
npx skills add . --skill codebase-understanding -g -a codex -y --copy
npx skills add . --skill daily-webnovel-writing-knowledge -g -a codex -y --copy
npx skills add . --skill teddynote-langchain-rag -g -a codex -y --copy
npx skills ls -g --json
```

macOS/Linux codebase-understanding smoke:

```bash
python3 -m py_compile skills/codebase-understanding/scripts/*.py
python3 skills/codebase-understanding/scripts/scan_codebase.py . --out .codebase-understanding/codebase-map.json
python3 skills/codebase-understanding/scripts/validate_graph.py .codebase-understanding/codebase-map.json
python3 skills/codebase-understanding/scripts/explain_graph.py .codebase-understanding/codebase-map.json README.md --root .
python3 skills/codebase-understanding/scripts/build_chat_prompt.py .codebase-understanding/codebase-map.json --q "backend architecture"
python3 skills/codebase-understanding/scripts/semantic_graph.py run .codebase-understanding/codebase-map.json --root . --packs-dir .codebase-understanding/semantic-packs --annotations-out .codebase-understanding/semantic-annotations.json --out .codebase-understanding/codebase-map.json
python3 skills/codebase-understanding/scripts/write_diff_overlay.py .codebase-understanding/codebase-map.json --changed-file README.md --out .codebase-understanding/diff-overlay.json
python3 skills/codebase-understanding/scripts/understand_codebase.py analyze . --no-dashboard
python3 skills/codebase-understanding/scripts/understand_codebase.py chat . "backend architecture" --graph .codebase-understanding/codebase-map.json
python3 skills/codebase-understanding/scripts/understand_codebase.py explain . README.md --graph .codebase-understanding/codebase-map.json
python3 skills/codebase-understanding/scripts/understand_codebase.py diff . --graph .codebase-understanding/codebase-map.json --changed-file README.md
python3 skills/codebase-understanding/scripts/understand_codebase.py onboard . --graph .codebase-understanding/codebase-map.json
python3 skills/codebase-understanding/scripts/understand_codebase.py study . --graph .codebase-understanding/codebase-map.json --limit 20
python3 skills/codebase-understanding/scripts/understand_codebase.py semantic . --graph .codebase-understanding/codebase-map.json
npx skills add . --skill codebase-understanding -g -a codex -y --copy
```

Release checklist:

```powershell
npx -y skills add . --list
npx -y skills add munlucky/moonshotnote-skills --skill moonshotnote-ocr --list
npx -y skills add munlucky/moonshotnote-skills --skill fastapi-clean-architecture --list
npx -y skills add munlucky/moonshotnote-skills --skill text-knowledge-skill-builder --list
npx -y skills add munlucky/moonshotnote-skills --skill tidy-first --list
npx -y skills add munlucky/moonshotnote-skills --skill backend-architecture --list
npx -y skills add munlucky/moonshotnote-skills --skill modern-java-in-action --list
npx -y skills add munlucky/moonshotnote-skills --skill spring-modern-api --list
npx -y skills add munlucky/moonshotnote-skills --skill python-architecture-patterns --list
npx -y skills add munlucky/moonshotnote-skills --skill domain-driven-design-first-steps --list
npx -y skills add munlucky/moonshotnote-skills --skill codebase-understanding --list
npx -y skills add munlucky/moonshotnote-skills --skill daily-webnovel-writing-knowledge --list
npx -y skills add munlucky/moonshotnote-skills --skill teddynote-langchain-rag --list
```

The GitHub Actions workflow in `.github/workflows/validate.yml` runs lightweight publish checks only: manifest validation, Python syntax compilation, and `npx skills add . --list`. It intentionally does not install PaddleOCR, Surya, or model files.
The main validation job runs on both `ubuntu-latest` and `macos-latest`; `codebase-understanding` also has a CI smoke for scan, validate, query, explain, chat prompt, diff overlay, and dashboard HTTP endpoints.
