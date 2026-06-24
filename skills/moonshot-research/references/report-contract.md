# Report Contract

Use this for medium or long research deliverables. For short answers, compress the same structure.

When `scripts/research_harness.py` is used, build the final answer from `report.md`, `evidence.json`, and `claim-ledger.json`. The generated `report.md` is an evidence pack, not a substitute for Codex synthesis.

## Required Sections

1. **Answer**
   - Direct conclusion or ranked list.
   - 3-6 key findings with citations.
   - Confidence level: high, medium, low.

2. **Method**
   - Research date.
   - Assumed time window.
   - Source lanes attempted.
   - Important access limits.

3. **Evidence Table**
   - Claim or entity.
   - Source URL.
   - Source type: primary, platform sample, media, discussion, documentation, dataset, inference.
   - Date observed or published.
   - Evidence summary.
   - Confidence.

4. **Claim Ledger**
   - Claim ID.
   - Claim text.
   - Evidence URL(s).
   - Status: source-observed, contradicted, access-limited, or needs-follow-up.
   - Confidence and unresolved checks.

5. **Synthesis**
   - Explain patterns across sources.
   - Separate facts from inference.
   - Explain disagreements or missing data.

6. **Limits And Next Searches**
   - Blocked lanes.
   - Weak evidence.
   - Queries or data sources that would improve confidence.

## Trend Scoring

When ranking "hot" brands, tools, technologies, products, or narratives, score with these factors:

- Recency: newer public mentions or releases carry more weight for "hot".
- Velocity: repeated recent mentions across independent surfaces beat one viral post.
- Cross-source corroboration: X + Reddit + HN + GitHub/news is stronger than one platform.
- Source quality: primary sources and direct user discussions beat reposted summaries.
- Engagement quality: substantive comments, adoption reports, benchmarks, or purchases beat empty likes.
- Counter-evidence: complaints, corrections, dead repos, deleted posts, and bot-like promotion reduce confidence.

Never output a precise numeric ranking unless the collection method actually measured comparable quantities.
