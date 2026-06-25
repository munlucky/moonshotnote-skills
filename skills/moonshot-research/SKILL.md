---
name: moonshot-research
description: Maximum-saturation public-web research workflow for Codex. Use when the user explicitly invokes moonshot-research, /moonshot-research, or $moonshot-research, or asks to replace GPT/Gemini Deep Research with fast cited research across web search, X/Twitter, Reddit, Hacker News, GitHub, YouTube, papers, news, product pages, reviews, or public datasets. Designed for trend discovery, competitive research, market/brand scans, technical landscape research, source triangulation, contradiction checks, and report generation from current public evidence.
---

# Moonshot Research

Run a public-web research harness: plan the search, saturate relevant source lanes, keep evidence structured, iterate on gaps, and return a cited report. Use the bundled CLI when live public-web collection is needed; use the written workflow when the environment already provides stronger native search/browser tools.

## Operating Contract

- Use public sources only. Stop at logins, paywalls, private APIs, CAPTCHAs, or credential prompts and report the access boundary.
- Browse or otherwise verify live web evidence for any current, latest, trending, price, legal, market, product, social, or company claim.
- Track every material claim to a source URL, retrieval route, date, and confidence.
- Do not treat `200 OK` as success by itself. Treat challenge pages, empty SPA shells, tiny bodies, WAF markers, and missing positive proof as failed or suspect fetches.
- Separate existence claims from actionability claims. For example, a job page existing or saying `상시채용` is not proof that applications are open; require an enabled apply button, rendered DOM proof, or a public status API.
- Prefer primary sources for technical claims: official docs, repos, release notes, standards, papers, issue trackers, or maintainer posts.
- Avoid long quotations. Summarize, cite, and quote only short fragments when wording itself matters.
- State absolute dates. For "recent", "hot", or "these days", default to the last 7 days unless the user gives a different window.
- Do not present X, Reddit, HN, or search-engine samples as complete platform firehose coverage.

## Workflow

1. **Frame the task.** Extract topic, target geography/language, time window, source lanes, output format, and decision criteria. Ask only if missing scope would materially change the answer; otherwise proceed with explicit assumptions.
2. **Run the harness.** Prefer `scripts/research_harness.py` for `search -> collect -> dedupe -> score -> report` when the task asks for current public-web evidence. Use narrow lanes for small tasks and all default lanes for trend discovery.
3. **Open source lanes.** Build separate lanes for the requested platforms and adjacent sources. Read `references/source-strategy.md` when X, Reddit, HN, GitHub, YouTube, product, brand, or blocked-site handling matters.
4. **Collect evidence.** Run broad queries first, then targeted follow-ups. Use advanced search operators, native public feeds/APIs where available, browser inspection, and page-specific metadata. Capture URLs, titles, authors, dates, metrics, snippets, and access failures.
5. **Cluster and score.** Group findings by entity, theme, claim, or trend. Score for recency, velocity, cross-source corroboration, source quality, and contradiction risk.
6. **Expand until convergence.** After the first pass, list gaps and contradictions. Run at least one targeted gap-fill round. Stop when a new round adds no material finding, the time budget is exhausted, or access boundaries block the remaining lanes.
7. **Verify brittle claims.** For numerical, technical, or policy claims, seek primary confirmation. For ambiguous claims, run disconfirming searches such as `site:`, exact-title searches, "criticism", "not true", "changelog", "issue", or date-bounded variants.
8. **Report.** Use `references/report-contract.md` for longer deliverables. For shorter answers, still include the answer, method note, key evidence, confidence, and unresolved limits.

## CLI Harness

Run from the skill directory or pass an absolute output path:

```powershell
py -3 scripts\research_harness.py "developer AI trends" --lanes web,reddit,hn,github,youtube,x --rounds 2 --limit-per-lane 5
```

```bash
python3 scripts/research_harness.py "developer AI trends" --lanes web,reddit,hn,github,youtube,x --rounds 2 --limit-per-lane 5
```

Artifacts:

- `output/research/<run-id>/evidence.json`: deduped and scored source evidence.
- `output/research/<run-id>/claim-ledger.json`: auditable claim ledger from top evidence.
- `output/research/<run-id>/run.json`: lane/query/failure metadata.
- `output/research/<run-id>/report.md`: source-grounded report pack for final synthesis.

Useful options:

- `--lanes web,reddit,hn,github,youtube,x`: choose source lanes.
- `--rounds 1`: disable expanded follow-up queries for a quick pass.
- `--escalation basic|public|tls|browser|full`: control blocked-page escalation.
- `--verification-profile apply-availability`: require enabled apply-action proof and capture rendered network API candidates. Use this for job/application availability checks.
- `--success-selector "<selector>"`: require an enabled rendered element before a page counts as positive proof.
- `--failure-selector "<selector>"`: mark the claim failed when rendered failure proof is present.
- `--proof-text "<text>"`: require text proof in addition to a successful fetch.
- `--real-chrome --chrome-profile <dir>`: escalate browser fetches to system Chrome with a persistent profile when bundled/headless Chromium is blocked.
- `--capture-network`: record rendered `/api`, `/graphql`, `.json`, `job`, `apply`, or `status` request URLs with sensitive query keys stripped.
- `--media-metadata`: use optional `yt-dlp` metadata/caption discovery for media URLs.
- `--no-fetch-pages`: keep only search/API metadata when page fetching is slow or blocked.
- `--out <dir>`: write artifacts outside the ignored skill `output/` tree when the user needs a durable deliverable.
- `--print-capabilities`: show whether optional `curl_cffi`, `playwright`, and `yt-dlp` support is available.

Optional escalation dependencies:

```powershell
py -3 -m pip install -r scripts\requirements-optional.txt
py -3 -m playwright install chromium
```

```bash
python3 -m pip install -r scripts/requirements-optional.txt
python3 -m playwright install chromium
```

Escalation behavior:

- `basic`: Phase 0 direct `urllib` fetch with validation.
- `public`: Phase 0 plus Phase 1 public URL variants such as oEmbed, `.json`, `/rss`, mobile host, and Jina reader.
- `tls`: Phase 0/1 plus Phase 2 optional `curl_cffi` browser TLS impersonation with origin warmup, referer, cookies, and Safari/Chrome/Firefox identities.
- `browser`: Phase 0/1 plus Phase 3 optional Playwright rendering.
- `full`: Phase 0 direct, Phase 1 public routes, Phase 2 TLS impersonation, then Phase 3 browser rendering.

Positive-proof example for job/application checks:

```powershell
py -3 scripts\research_harness.py "Wanted example company backend job" --lanes web --rounds 1 --escalation full --verification-profile apply-availability --real-chrome --chrome-profile "$env:TEMP\moonshot-research-chrome"
```

When a rendered page requires login, private session state, or a CAPTCHA to know whether the button is enabled, report `unknown-auth-required` or the recorded access boundary. Do not infer availability from static listing copy.

After running, read `report.md`, inspect `claim-ledger.json` for auditability, and synthesize the user-facing answer with citations. Do not treat the generated ranking as a statistical platform-wide measurement.

## Parallel Research

The CLI already parallelizes lane and page fetches locally. When the user explicitly asks for parallel agents or the environment provides an approved multi-agent workflow, split by non-overlapping lanes:

- Platform lanes: X, Reddit, HN, GitHub, news/blogs, papers, product/review sites.
- Question lanes: discovery, verification, counter-evidence, metrics, background.
- Output lanes: evidence table, synthesis, visual/report packaging.

Require each worker to return only source-grounded findings with URLs, dates, search route, confidence, and open questions. Merge by claim, not by worker narrative, so duplicate evidence reinforces confidence instead of bloating the report.

## Blocked Or Sparse Sources

Use an escalation ladder and stop honestly:

1. Phase 0 direct fetch; reject 403/WAF/challenge/small body/empty SPA as terminal success.
2. Phase 1 public endpoints, feeds, `.json`, `/rss`, oEmbed, mobile pages, Jina reader, official search pages, or documented APIs.
3. Phase 2 optional TLS impersonation with `curl_cffi`, origin warmup, referer chain, and cookies.
4. Phase 3 browser automation; use system Chrome with a persistent profile when ordinary headless Chromium is blocked and the user request needs that proof.
5. Rendered-page inspection: evaluate success/failure selectors and inspect network requests for public `/api`, `/graphql`, `.json`, status, job, or apply endpoints.
6. Boundary report: `authentication required`, `paywalled`, `blocked by bot challenge`, `positive proof failed`, `not indexed`, or `no public evidence found`.

Never bypass authentication, defeat paywalls, use leaked credentials, or imply that sparse public evidence proves absence.

## Output Rules

- Lead with the answer, not a diary of searches.
- Include sources as links next to the claims they support.
- Distinguish facts, estimates, inferences, and hypotheses.
- Include a "Limits" or "Unknowns" note for blocked lanes, weak samples, or missing primary data.
- For trend/brand rankings, show the scoring basis and avoid false precision.
- For Korean users, answer in Korean unless the user asks otherwise.
