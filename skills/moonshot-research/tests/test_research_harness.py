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
        self.assertEqual(rh.detect_access_status(200, "Please sign in to continue"), "possibly blocked")
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

    def test_public_variant_escalation_returns_variant_route(self):
        original_http_get = rh.http_get
        calls = []

        def fake_http_get(url, timeout=12.0, accept="*/*"):
            calls.append(url)
            if len(calls) == 1:
                return 403, url, "captcha required"
            return 200, url, "<html><title>Variant OK</title><body>public page text</body></html>"

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
        self.assertEqual(set(capabilities), {"curl_cffi", "playwright", "yt_dlp"})

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
                )
                result = rh.run_research(args)
                self.assertEqual(result["out_dir"], tmp)
                self.assertTrue((Path(tmp) / "report.md").is_file())
        finally:
            rh.collect_lane = original_collect_lane
            rh.enrich_items = original_enrich_items


if __name__ == "__main__":
    unittest.main()
