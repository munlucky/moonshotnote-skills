# Source Strategy

Use this when a research task depends on specific public platforms, current trends, or blocked/sparse sources.

The bundled `scripts/research_harness.py` implements the default public collection path with no API keys:

- `web`: DuckDuckGo HTML result discovery.
- `reddit`: Reddit public JSON search, then `site:reddit.com` fallback.
- `hn`: Hacker News Algolia API.
- `github`: GitHub repository search API, then `site:github.com` fallback.
- `youtube`: public search-engine discovery for YouTube watch URLs.
- `x`: public search-engine discovery for X/Twitter URLs.

It deduplicates URLs, fetches public page metadata when possible, scans for access boundaries, scores evidence, and writes a claim ledger.

Optional escalation is available when dependencies are installed:

- `--escalation tls`: adds `curl_cffi` with browser TLS identities.
- `--escalation browser`: adds Playwright Chromium for public page rendering and JSON-LD/OGP extraction.
- `--escalation full`: tries public variants, TLS impersonation, then browser rendering.
- `--media-metadata`: adds `yt-dlp` metadata and caption language discovery for YouTube/media URLs.

Run `scripts/research_harness.py --print-capabilities` before assuming optional escalation is active.

## Query Planning

- Generate 3-8 seed queries from the user's wording: exact phrase, synonyms, acronyms, Korean/English variants, competitor names, ticker/product names, hashtags, and misspellings.
- For "hot" or "trending", combine recency terms with engagement terms: `viral`, `popular`, `launch`, `review`, `complaint`, `pricing`, `benchmark`, `show hn`, `reddit`, `x.com`, `site:`.
- Run at least one disconfirming query for high-impact conclusions.
- Record the search route, not just the destination URL, when ranking depends on platform visibility.

## X / Twitter

X public access is often incomplete. Treat results as sampled evidence.

- Try web search with `site:x.com OR site:twitter.com`, exact brand/topic names, hashtags, account names, and date terms.
- If an X page opens in a browser, capture visible author, handle, timestamp, engagement metrics, media/text summary, and URL.
- For known tweet URLs, public oEmbed or metadata may expose author/title text even when the page is hard to render.
- Cross-check important X trends against news, Reddit, HN, GitHub, YouTube, brand pages, or third-party coverage before ranking.
- Report access limits clearly: logged-out search gaps, unavailable engagement counts, deleted posts, or region/language bias.

## Reddit

- Prefer native subreddit context when the user names a community.
- Try Reddit search pages, `site:reddit.com/r/<subreddit>`, public JSON/RSS variants, and search-engine snippets.
- Capture subreddit, post title, author if visible, score/comment count if visible, timestamp, top themes, and dissenting comments.
- Treat one subreddit as one community sample, not the entire market.

## Hacker News

- Use HN item pages for final citations when possible.
- Algolia HN search is useful for discovery by date, points, comments, title, URL, author, and tags.
- For technical trends, compare HN discussion with upstream repos, docs, release notes, benchmarks, or issue trackers.

## GitHub And Developer Signals

- Search repositories, releases, issues, pull requests, discussions, stars, forks, commit recency, and dependency manifests.
- Prefer official repository data over third-party summaries.
- Check whether a repo is active, archived, newly renamed, or vendor-owned before using it as evidence of adoption.

## YouTube, Blogs, And News

- Use official video pages, captions/transcripts when available, channel metadata, publish dates, and description links.
- For news/blogs, prefer original reporting, official company posts, release notes, or named-source interviews.
- Do not treat SEO listicles as primary evidence unless the task is specifically about SEO visibility.

## Brand, Product, And Market Research

- Combine social signals with primary pages, product listings, reviews, app-store data, press, influencer mentions, and search interest proxies.
- Separate "consumer buzz", "sales traction", "founder/investor attention", and "developer adoption"; these are different claims.
- Use rankings only after explaining the weighting.

## Blocked Source Handling

- Try public APIs/feeds first, then search cache/snippets, mobile or metadata surfaces, and browser inspection.
- Stop at authentication, paywalls, private groups, or CAPTCHA walls.
- Write down failed routes so the final report does not overstate coverage.

For CLI runs, blocked lanes appear as `access boundary` evidence items or entries in `run.json.failures`. Use those records in the final "Limits" section.
