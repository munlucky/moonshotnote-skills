import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import research_harness as rh


class ResearchHarnessTest(unittest.TestCase):
    def test_canonicalize_url_removes_tracking_and_www(self):
        url = "https://www.Example.com/path/?utm_source=x&a=1&fbclid=abc"
        self.assertEqual(rh.canonicalize_url(url), "https://example.com/path?a=1")

    def test_dedupe_keeps_stronger_item(self):
        weak = rh.EvidenceItem(lane="web", query="q", url="https://example.com/?utm_source=x", title="weak")
        strong = rh.EvidenceItem(
            lane="web",
            query="q",
            url="https://www.example.com/",
            title="strong",
            summary="more detail",
            metric_score=10,
        )
        deduped = rh.dedupe_items([weak, strong])
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0].title, "strong")

    def test_detect_access_status_marks_login_and_paywall(self):
        self.assertEqual(rh.detect_access_status(401, ""), "authentication required")
        self.assertEqual(rh.detect_access_status(200, "Please sign in to continue"), "authentication required")
        self.assertEqual(rh.detect_access_status(403, "captcha required"), "blocked by bot challenge")

    def test_score_items_prefers_query_overlap_and_metrics(self):
        item = rh.EvidenceItem(
            lane="hn",
            query="developer ai trends",
            url="https://news.ycombinator.com/item?id=1",
            title="Developer AI trends",
            summary="Developer tools and AI agents",
            metric_score=100,
            access_status="ok",
        )
        scored = rh.score_items([item], "developer ai trends")
        self.assertGreater(scored[0].score, 0)
        self.assertIn(scored[0].confidence, {"medium", "high"})

    def test_parse_duckduckgo_lite_uddg_links(self):
        body = """
        <html><body>
          <a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fgithub.com%2Flangchain-ai%2Fopen-swe&amp;rut=x">
            GitHub - langchain-ai/open-swe
          </a>
        </body></html>
        """
        results = rh.parse_duckduckgo_results(body, 3)
        self.assertEqual(results[0]["url"], "https://github.com/langchain-ai/open-swe")
        self.assertEqual(results[0]["title"], "GitHub - langchain-ai/open-swe")

    def test_search_web_falls_back_after_duckduckgo_202(self):
        original_http_get = rh.http_get
        calls = []

        def fake_http_get(url, timeout=12.0, accept="*/*"):
            calls.append(url)
            if "duckduckgo.com/html" in url:
                return 202, url, "<html><body>accepted</body></html>"
            return (
                200,
                url,
                '<html><body><a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com">Example</a></body></html>',
            )

        try:
            rh.http_get = fake_http_get
            results = rh.search_web("Open SWE", 3, 0.1)
            self.assertEqual(results[0]["url"], "https://example.com")
            self.assertEqual(results[0]["route"], "duckduckgo-lite")
            self.assertGreaterEqual(len(calls), 2)
        finally:
            rh.http_get = original_http_get

    def test_focused_queries_extracts_source_specific_terms(self):
        queries = rh.focused_queries(
            "AI agent harness loop engineering open source SWE-bench OpenHands Inspect evals LangGraph cases"
        )
        self.assertIn("agent harness evaluation", queries)
        self.assertIn("SWE-bench harness", queries)
        self.assertIn("OpenHands software agent", queries)
        self.assertIn("LangGraph agent workflow", queries)

    def test_collect_github_retries_focused_query_when_seed_has_no_results(self):
        original_http_get = rh.http_get
        calls = []

        def fake_http_get(url, timeout=12.0, accept="*/*"):
            calls.append(url)
            if "agent+harness+evaluation" not in url:
                return 200, url, json.dumps({"items": []})
            return (
                200,
                url,
                json.dumps(
                    {
                        "items": [
                            {
                                "html_url": "https://github.com/example/agent-harness",
                                "full_name": "example/agent-harness",
                                "description": "Agent harness",
                                "updated_at": "2026-06-24T00:00:00Z",
                                "stargazers_count": 10,
                                "forks_count": 2,
                                "language": "Python",
                            }
                        ]
                    }
                ),
            )

        try:
            rh.http_get = fake_http_get
            items = rh.collect_github("AI agent harness loop engineering", 3, 0.1)
            self.assertEqual(items[0].url, "https://github.com/example/agent-harness")
            self.assertIn("agent+harness+evaluation", calls[-1])
        finally:
            rh.http_get = original_http_get

    def test_write_report_pack_creates_expected_artifacts(self):
        item = rh.EvidenceItem(
            lane="web",
            query="q",
            url="https://example.com",
            title="Example",
            summary="Evidence",
            observed_at="2026-06-24T00:00:00+00:00",
            score=5,
            confidence="medium",
        )
        pack = rh.build_report_pack([item], "q", ["web"], ["q"], "2026-06-24T00:00:00+00:00", [])
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            rh.write_report_pack(out_dir, pack)
            self.assertTrue((out_dir / "evidence.json").is_file())
            self.assertTrue((out_dir / "claim-ledger.json").is_file())
            self.assertTrue((out_dir / "report.md").is_file())
            evidence = json.loads((out_dir / "evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence[0]["title"], "Example")

    def test_validate_response_treats_200_challenge_as_suspect(self):
        result = rh.validate_response(200, "<html>cf-chl verify you are human</html>")
        self.assertFalse(result.usable)
        self.assertEqual(result.verdict, "challenge_page")

    def test_validate_response_requires_positive_proof_when_configured(self):
        missing = rh.validate_response(
            200,
            "<html><body>" + ("상시채용 " * 80) + "</body></html>",
            success_selectors=["button:has-text('지원하기')"],
        )
        self.assertFalse(missing.usable)
        self.assertIn("required_success_selector_missing", missing.reasons)
        matched = rh.validate_response(
            200,
            "<html><body>" + ("content " * 80) + "</body></html>",
            success_selectors=["button:has-text('지원하기')"],
            browser_proof={"success_selectors": ["button:has-text('지원하기')"]},
        )
        self.assertTrue(matched.usable)
        self.assertEqual(matched.verdict, "strong_ok")

    def test_apply_availability_profile_forces_browser_network_capture(self):
        args = Namespace(
            success_selector=None,
            failure_selector=None,
            proof_text=None,
            verification_profile="apply-availability",
            min_body_chars=300,
            real_chrome=False,
            headful=False,
            chrome_profile=None,
            capture_network=False,
        )
        options = rh.verification_options(args)
        self.assertTrue(options["requires_browser"])
        self.assertTrue(options["capture_network"])
        self.assertIn("button:has-text('지원하기')", options["success_selectors"])

    def test_sanitize_observed_url_drops_sensitive_query_keys(self):
        url = rh.sanitize_observed_url("https://example.com/api/job?token=secret&id=1&signature=sig")
        self.assertEqual(url, "https://example.com/api/job?id=1")

    def test_public_variant_escalation_returns_variant_route(self):
        original_http_get = rh.http_get
        calls = []

        def fake_http_get(url, timeout=12.0, accept="*/*"):
            calls.append(url)
            if len(calls) == 1:
                return 403, url, "captcha required"
            return 200, url, "<html><title>Variant OK</title><body>" + ("public page text " * 40) + "</body></html>"

        try:
            rh.http_get = fake_http_get
            status, final_url, body, route, attempts = rh.fetch_public_content(
                "https://www.reddit.com/r/test/comments/abc/example",
                timeout=0.1,
                accept="text/html",
                escalation="public",
            )
            self.assertEqual(status, 200)
            self.assertIn(route, {"reddit-json", "reddit-rss", "json-suffix", "mobile-host", "rss-suffix"})
            self.assertGreaterEqual(len(attempts), 2)
            self.assertIn("Variant OK", body)
            self.assertEqual(final_url, calls[-1])
        finally:
            rh.http_get = original_http_get

    def test_200_challenge_continues_to_public_variant(self):
        original_http_get = rh.http_get
        calls = []

        def fake_http_get(url, timeout=12.0, accept="*/*"):
            calls.append(url)
            if len(calls) == 1:
                return 200, url, "<html><body>cf-chl verify you are human</body></html>"
            return 200, url, "<html><title>Readable</title><body>" + ("public evidence " * 40) + "</body></html>"

        try:
            rh.http_get = fake_http_get
            status, _, body, route, attempts = rh.fetch_public_content(
                "https://www.reddit.com/r/test/comments/abc/example",
                timeout=0.1,
                accept="text/html",
                escalation="public",
            )
            self.assertEqual(status, 200)
            self.assertNotEqual(route, "urllib")
            self.assertEqual(attempts[0]["verdict"], "challenge_page")
            self.assertIn("Readable", body)
        finally:
            rh.http_get = original_http_get

    def test_basic_escalation_does_not_try_variants(self):
        original_http_get = rh.http_get
        calls = []

        def fake_http_get(url, timeout=12.0, accept="*/*"):
            calls.append(url)
            return 403, url, "captcha required"

        try:
            rh.http_get = fake_http_get
            status, _, _, route, attempts = rh.fetch_public_content(
                "https://example.com/page",
                timeout=0.1,
                accept="text/html",
                escalation="basic",
            )
            self.assertEqual(status, 403)
            self.assertEqual(route, "urllib")
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(attempts), 1)
        finally:
            rh.http_get = original_http_get

    def test_optional_capabilities_has_expected_keys(self):
        capabilities = rh.optional_capabilities()
        self.assertEqual(set(capabilities), {"curl_cffi", "playwright", "system_chrome", "yt_dlp"})

    def test_default_output_dir_is_under_skill_output(self):
        args = Namespace(query="developer ai", out=None)
        out_dir = rh.resolve_output_dir(args)
        try:
            self.assertIn("moonshot-research", str(out_dir))
            self.assertIn("output", out_dir.parts)
            self.assertTrue(out_dir.is_dir())
        finally:
            # Remove the empty run directory created by resolve_output_dir.
            out_dir.rmdir()

    def test_run_research_with_mocked_collector(self):
        original_collect_lane = rh.collect_lane
        original_enrich_items = rh.enrich_items
        try:
            rh.collect_lane = lambda lane, query, limit, timeout: [
                rh.EvidenceItem(lane=lane, query=query, url=f"https://example.com/{lane}", title=f"{lane} {query}")
            ]
            rh.enrich_items = lambda items, timeout, workers, escalation="public", media_metadata=False: items
            rh.enrich_items = lambda *args, **kwargs: args[0]
            with tempfile.TemporaryDirectory() as tmp:
                args = Namespace(
                    query="developer ai",
                    lanes="web,hn",
                    rounds=1,
                    limit_per_lane=2,
                    timeout=0.1,
                    workers=2,
                    out=tmp,
                    fetch_pages=True,
                    escalation="public",
                    media_metadata=False,
                    success_selector=None,
                    failure_selector=None,
                    proof_text=None,
                    verification_profile="",
                    min_body_chars=300,
                    real_chrome=False,
                    headful=False,
                    chrome_profile=None,
                    capture_network=False,
                )
                result = rh.run_research(args)
                self.assertEqual(result["out_dir"], tmp)
                self.assertTrue((Path(tmp) / "report.md").is_file())
        finally:
            rh.collect_lane = original_collect_lane
            rh.enrich_items = original_enrich_items


if __name__ == "__main__":
    unittest.main()
