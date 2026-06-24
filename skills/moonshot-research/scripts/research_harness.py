#!/usr/bin/env python3
"""Public-web research harness for the moonshot-research skill.

The harness deliberately uses only Python's standard library. It is not a
private-data crawler and it does not bypass authentication. It fans out across
public source lanes, records access boundaries, deduplicates evidence, scores
items, and writes a report pack for Codex to synthesize from.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import datetime as dt
import hashlib
import html
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable


DEFAULT_LANES = ("web", "reddit", "hn", "github", "youtube", "x")
ESCALATION_LEVELS = ("basic", "public", "tls", "browser", "full")
USER_AGENT = (
    "Mozilla/5.0 (compatible; MoonshotResearch/1.0; "
    "+https://github.com/munlucky/moonshotnote-skills)"
)
BLOCK_PATTERNS = (
    "authentication required",
    "sign in",
    "log in",
    "login",
    "paywall",
    "subscribe to continue",
    "captcha",
    "cf-chl",
    "access denied",
    "forbidden",
    "waf",
)


@dataclasses.dataclass
class EvidenceItem:
    lane: str
    query: str
    url: str
    title: str = ""
    summary: str = ""
    source_type: str = "platform sample"
    published_at: str = ""
    observed_at: str = ""
    metric_score: float = 0.0
    score: float = 0.0
    confidence: str = "low"
    access_status: str = "ok"
    route: str = ""
    raw: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class SearchResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._in_link = False
        self._current_href = ""
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr_map = {key: value or "" for key, value in attrs}
        href = attr_map.get("href", "")
        css = attr_map.get("class", "")
        if "result__a" in css or href.startswith("//duckduckgo.com/l/"):
            self._in_link = True
            self._current_href = href
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._in_link:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_link:
            title = normalize_space(" ".join(self._current_text))
            url = unwrap_duckduckgo_url(self._current_href)
            if url and title:
                self.results.append({"url": url, "title": title})
            self._in_link = False
            self._current_href = ""
            self._current_text = []


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.meta: dict[str, str] = {}
        self.json_ld: list[str] = []
        self._capture_title = False
        self._capture_script = False
        self._skip_depth = 0
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        if tag == "title":
            self._capture_title = True
        elif tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            if tag == "script" and attr_map.get("type") == "application/ld+json":
                self._capture_script = True
        elif tag == "meta":
            key = attr_map.get("property") or attr_map.get("name")
            content = attr_map.get("content")
            if key and content:
                self.meta[key.lower()] = html.unescape(content)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._capture_title = False
        elif tag in {"script", "style", "noscript"}:
            self._skip_depth = max(0, self._skip_depth - 1)
            self._capture_script = False

    def handle_data(self, data: str) -> None:
        text = normalize_space(data)
        if not text:
            return
        if self._capture_title:
            self.title = normalize_space(f"{self.title} {text}")
        elif self._capture_script:
            self.json_ld.append(text)
        elif self._skip_depth == 0:
            self._text.append(text)

    @property
    def text(self) -> str:
        return normalize_space(" ".join(self._text))


def extract_json_metadata(body: str) -> tuple[str, str, str]:
    try:
        payload = json.loads(body)
    except Exception:
        return "", "", ""
    candidates: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        candidates.append(payload)
        if isinstance(payload.get("data"), dict):
            candidates.append(payload["data"])
        if isinstance(payload.get("items"), list):
            candidates.extend(item for item in payload["items"][:3] if isinstance(item, dict))
    elif isinstance(payload, list):
        candidates.extend(item for item in payload[:3] if isinstance(item, dict))

    for candidate in candidates:
        title = (
            candidate.get("title")
            or candidate.get("author_name")
            or candidate.get("name")
            or candidate.get("full_name")
            or ""
        )
        summary = (
            candidate.get("description")
            or candidate.get("selftext")
            or candidate.get("text")
            or candidate.get("html")
            or candidate.get("summary")
            or ""
        )
        published = (
            candidate.get("published_at")
            or candidate.get("created_at")
            or candidate.get("updated_at")
            or candidate.get("date")
            or ""
        )
        if title or summary:
            return normalize_space(str(title)), normalize_space(str(summary)), normalize_space(str(published))
    return "", "", ""


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def unwrap_duckduckgo_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    if "uddg" in query:
        return query["uddg"][0]
    return url


def canonicalize_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    query_pairs = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower()
        not in {"fbclid", "gclid", "igshid", "mc_cid", "mc_eid", "ref", "source"}
    ]
    query = urllib.parse.urlencode(query_pairs, doseq=True)
    path = parsed.path.rstrip("/") or "/"
    return urllib.parse.urlunparse((scheme, netloc, path, "", query, ""))


def http_get(url: str, timeout: float = 12.0, accept: str = "*/*") -> tuple[int, str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read(2_000_000).decode(charset, errors="replace")
            return response.status, response.geturl(), body
    except urllib.error.HTTPError as exc:
        body = exc.read(200_000).decode("utf-8", errors="replace")
        return exc.code, url, body
    except Exception as exc:  # network evidence, not implementation failure
        return 0, url, f"{type(exc).__name__}: {exc}"


def optional_capabilities() -> dict[str, Any]:
    return {
        "curl_cffi": importlib.util.find_spec("curl_cffi") is not None,
        "playwright": importlib.util.find_spec("playwright") is not None,
        "yt_dlp": shutil.which("yt-dlp") is not None or importlib.util.find_spec("yt_dlp") is not None,
    }


def public_url_variants(url: str) -> list[tuple[str, str]]:
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return []
    variants: list[tuple[str, str]] = []
    host = parsed.netloc
    path = parsed.path or "/"
    if host in {"x.com", "twitter.com"} or host.endswith(".x.com") or host.endswith(".twitter.com"):
        variants.append(("x-oembed", "https://publish.twitter.com/oembed?" + urllib.parse.urlencode({"url": url})))
    if "reddit.com" in host:
        variants.append(("reddit-json", urllib.parse.urlunparse(parsed._replace(path=path.rstrip("/") + ".json"))))
        variants.append(("reddit-rss", urllib.parse.urlunparse(parsed._replace(path=path.rstrip("/") + ".rss"))))
    if "youtube.com" in host or "youtu.be" in host:
        video_id = youtube_video_id(url)
        if video_id:
            variants.append(
                (
                    "youtube-oembed",
                    "https://www.youtube.com/oembed?" + urllib.parse.urlencode({"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"}),
                )
            )
    if path != "/":
        variants.append(("json-suffix", urllib.parse.urlunparse(parsed._replace(path=path.rstrip("/") + ".json"))))
    if not host.startswith("m.") and not host.startswith("mobile."):
        variants.append(("mobile-host", urllib.parse.urlunparse(parsed._replace(netloc="m." + host))))
    variants.append(("rss-suffix", urllib.parse.urlunparse(parsed._replace(path=path.rstrip("/") + "/rss"))))
    return [(name, variant) for name, variant in variants if variant != url]


def youtube_video_id(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.endswith("youtu.be"):
        return parsed.path.strip("/")
    query = urllib.parse.parse_qs(parsed.query)
    if "v" in query:
        return query["v"][0]
    return ""


def curl_cffi_get(url: str, timeout: float, accept: str) -> tuple[int, str, str, str]:
    try:
        from curl_cffi import requests as curl_requests  # type: ignore
    except Exception as exc:
        return 0, url, f"curl_cffi unavailable: {exc}", "tls-unavailable"
    last_error = ""
    for identity in ("chrome", "safari", "firefox"):
        try:
            response = curl_requests.get(
                url,
                timeout=timeout,
                impersonate=identity,
                headers={"Accept": accept, "Accept-Language": "en-US,en;q=0.9,ko;q=0.8"},
            )
            return response.status_code, str(response.url), response.text, f"curl-cffi-{identity}"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
    return 0, url, last_error, "tls-failed"


def playwright_get(url: str, timeout: float) -> tuple[int, str, str, str]:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        return 0, url, f"playwright unavailable: {exc}", "browser-unavailable"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=USER_AGENT, locale="en-US")
                response = page.goto(url, wait_until="domcontentloaded", timeout=max(1000, int(timeout * 1000)))
                page.wait_for_timeout(500)
                body = page.content()
                status = response.status if response else 0
                final_url = page.url
            finally:
                browser.close()
        return status, final_url, body, "playwright-chromium"
    except Exception as exc:
        return 0, url, f"{type(exc).__name__}: {exc}", "browser-failed"


def yt_dlp_metadata(url: str, timeout: float) -> dict[str, Any] | None:
    command: list[str] | None = None
    executable = shutil.which("yt-dlp")
    if executable:
        command = [executable]
    elif importlib.util.find_spec("yt_dlp") is not None:
        command = [sys.executable, "-m", "yt_dlp"]
    if not command:
        return None
    full_command = [
        *command,
        "--dump-json",
        "--skip-download",
        "--no-playlist",
        "--no-warnings",
        url,
    ]
    try:
        completed = subprocess.run(
            full_command,
            check=False,
            capture_output=True,
            text=True,
            timeout=max(timeout, 3.0),
        )
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    if completed.returncode != 0:
        return {"error": normalize_space(completed.stderr)[:500]}
    try:
        payload = json.loads(completed.stdout.splitlines()[0])
    except Exception as exc:
        return {"error": f"invalid yt-dlp json: {exc}"}
    subtitles = payload.get("subtitles") or {}
    automatic_captions = payload.get("automatic_captions") or {}
    return {
        "title": payload.get("title") or "",
        "description": payload.get("description") or "",
        "upload_date": payload.get("upload_date") or "",
        "channel": payload.get("channel") or payload.get("uploader") or "",
        "duration": payload.get("duration"),
        "view_count": payload.get("view_count"),
        "subtitles": sorted(subtitles.keys()),
        "automatic_captions": sorted(automatic_captions.keys()),
    }


def fetch_public_content(
    url: str,
    timeout: float,
    accept: str,
    escalation: str,
) -> tuple[int, str, str, str, list[dict[str, str]]]:
    attempts: list[dict[str, str]] = []
    status, final_url, body = http_get(url, timeout=timeout, accept=accept)
    route = "urllib"
    attempts.append({"route": route, "url": final_url, "status": str(status), "access": detect_access_status(status, body)})
    if is_usable_public_response(status, body) or escalation == "basic":
        return status, final_url, body, route, attempts

    if escalation in {"public", "tls", "browser", "full"}:
        for variant_name, variant_url in public_url_variants(url):
            v_status, v_final_url, v_body = http_get(variant_url, timeout=timeout, accept=accept)
            attempts.append(
                {
                    "route": variant_name,
                    "url": v_final_url,
                    "status": str(v_status),
                    "access": detect_access_status(v_status, v_body),
                }
            )
            if is_usable_public_response(v_status, v_body):
                return v_status, v_final_url, v_body, variant_name, attempts

    if escalation in {"tls", "full"}:
        c_status, c_final_url, c_body, c_route = curl_cffi_get(url, timeout, accept)
        attempts.append({"route": c_route, "url": c_final_url, "status": str(c_status), "access": detect_access_status(c_status, c_body)})
        if is_usable_public_response(c_status, c_body):
            return c_status, c_final_url, c_body, c_route, attempts

    if escalation in {"browser", "full"}:
        b_status, b_final_url, b_body, b_route = playwright_get(url, timeout)
        attempts.append({"route": b_route, "url": b_final_url, "status": str(b_status), "access": detect_access_status(b_status, b_body)})
        if is_usable_public_response(b_status, b_body):
            return b_status, b_final_url, b_body, b_route, attempts

    return status, final_url, body, route, attempts


def is_usable_public_response(status: int, body: str) -> bool:
    return 200 <= status < 300 and detect_access_status(status, body) == "ok" and bool(normalize_space(body)[:80])


def detect_access_status(status: int, body: str) -> str:
    lower = body.lower()
    if status in {401, 402}:
        return "authentication required"
    if status in {403, 429, 503}:
        if "captcha" in lower or "cf-chl" in lower:
            return "blocked by bot challenge"
        return "blocked or rate limited"
    if status == 0:
        return "fetch failed"
    if any(pattern in lower for pattern in BLOCK_PATTERNS):
        return "possibly blocked"
    return "ok"


def extract_page(
    url: str,
    lane: str,
    query: str,
    route: str,
    timeout: float,
    escalation: str = "public",
    media_metadata: bool = False,
) -> EvidenceItem:
    status, final_url, body, fetch_route, attempts = fetch_public_content(
        url,
        timeout=timeout,
        accept="text/html,application/xhtml+xml,application/json",
        escalation=escalation,
    )
    observed = now_iso()
    access_status = detect_access_status(status, body)
    parser = TextExtractor()
    if body and body.lstrip().startswith("<"):
        try:
            parser.feed(body)
        except Exception:
            pass
    json_title, json_summary, json_published = extract_json_metadata(body) if body and body.lstrip().startswith(("{", "[")) else ("", "", "")
    title = parser.meta.get("og:title") or parser.meta.get("twitter:title") or parser.title
    summary = (
        parser.meta.get("og:description")
        or parser.meta.get("description")
        or parser.meta.get("twitter:description")
        or parser.text[:500]
    )
    published = (
        parser.meta.get("article:published_time")
        or parser.meta.get("og:updated_time")
        or parser.meta.get("date")
        or ""
    )
    title = title or json_title
    summary = summary or json_summary
    published = published or json_published
    if access_status != "ok" and not title:
        title = f"{access_status}: {canonicalize_url(final_url)}"
    media = None
    if media_metadata and ("youtube.com" in urllib.parse.urlparse(url).netloc or "youtu.be" in urllib.parse.urlparse(url).netloc):
        media = yt_dlp_metadata(url, timeout)
        if media and not media.get("error"):
            title = normalize_space(media.get("title") or title)
            summary = normalize_space(media.get("description") or summary)[:700]
            published = media.get("upload_date") or published
    return EvidenceItem(
        lane=lane,
        query=query,
        url=final_url,
        title=normalize_space(title),
        summary=normalize_space(summary)[:700],
        source_type=source_type_for_url(final_url, lane),
        published_at=published,
        observed_at=observed,
        access_status=access_status,
        route=f"{route}+{fetch_route}",
        raw={"http_status": status, "json_ld_count": len(parser.json_ld), "attempts": attempts, "media": media},
    )


def source_type_for_url(url: str, lane: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    if "github.com" in host:
        return "primary repository" if lane == "github" else "developer source"
    if "hn.algolia.com" in host or "news.ycombinator.com" in host:
        return "discussion"
    if "reddit.com" in host:
        return "platform sample"
    if "youtube.com" in host or "youtu.be" in host:
        return "media"
    if "x.com" in host or "twitter.com" in host:
        return "platform sample"
    return "web page"


def search_duckduckgo(query: str, limit: int, timeout: float) -> list[dict[str, str]]:
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    status, _, body = http_get(url, timeout=timeout, accept="text/html")
    if status != 200:
        return []
    parser = SearchResultParser()
    parser.feed(body)
    return parser.results[:limit]


def collect_web(query: str, limit: int, timeout: float) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            lane="web",
            query=query,
            url=result["url"],
            title=result["title"],
            observed_at=now_iso(),
            route="duckduckgo-html",
            source_type=source_type_for_url(result["url"], "web"),
        )
        for result in search_duckduckgo(query, limit, timeout)
    ]


def collect_site_search(lane: str, query: str, site_query: str, limit: int, timeout: float) -> list[EvidenceItem]:
    search_query = f"{query} {site_query}"
    return [
        EvidenceItem(
            lane=lane,
            query=search_query,
            url=result["url"],
            title=result["title"],
            observed_at=now_iso(),
            route="duckduckgo-site-search",
            source_type=source_type_for_url(result["url"], lane),
        )
        for result in search_duckduckgo(search_query, limit, timeout)
    ]


def collect_hn(query: str, limit: int, timeout: float) -> list[EvidenceItem]:
    params = urllib.parse.urlencode({"query": query, "tags": "story", "hitsPerPage": limit})
    status, _, body = http_get(
        f"https://hn.algolia.com/api/v1/search_by_date?{params}",
        timeout=timeout,
        accept="application/json",
    )
    if status != 200:
        return [boundary_item("hn", query, "https://hn.algolia.com/api/v1/search_by_date", status, body)]
    payload = json.loads(body)
    items: list[EvidenceItem] = []
    for hit in payload.get("hits", [])[:limit]:
        object_id = str(hit.get("objectID") or "")
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
        points = float(hit.get("points") or 0)
        comments = float(hit.get("num_comments") or 0)
        items.append(
            EvidenceItem(
                lane="hn",
                query=query,
                url=url,
                title=normalize_space(hit.get("title") or hit.get("story_title") or ""),
                summary=f"HN story: {points:g} points, {comments:g} comments",
                source_type="discussion",
                published_at=hit.get("created_at") or "",
                observed_at=now_iso(),
                metric_score=points + comments * 2,
                route="hn-algolia-api",
                raw={"object_id": object_id, "points": points, "comments": comments},
            )
        )
    return items


def collect_reddit(query: str, limit: int, timeout: float) -> list[EvidenceItem]:
    params = urllib.parse.urlencode({"q": query, "sort": "new", "limit": limit, "raw_json": 1})
    url = f"https://www.reddit.com/search.json?{params}"
    status, _, body = http_get(url, timeout=timeout, accept="application/json")
    if status != 200:
        fallback = collect_site_search("reddit", query, "site:reddit.com/r/", limit, timeout)
        return fallback or [boundary_item("reddit", query, url, status, body)]
    payload = json.loads(body)
    items: list[EvidenceItem] = []
    for child in payload.get("data", {}).get("children", [])[:limit]:
        data = child.get("data", {})
        permalink = data.get("permalink") or ""
        score = float(data.get("score") or 0)
        comments = float(data.get("num_comments") or 0)
        created = data.get("created_utc")
        published = ""
        if created:
            published = dt.datetime.fromtimestamp(float(created), tz=dt.timezone.utc).isoformat()
        items.append(
            EvidenceItem(
                lane="reddit",
                query=query,
                url=urllib.parse.urljoin("https://www.reddit.com", permalink),
                title=normalize_space(data.get("title") or ""),
                summary=normalize_space(data.get("selftext") or "")[:500],
                source_type="platform sample",
                published_at=published,
                observed_at=now_iso(),
                metric_score=score + comments * 2,
                route="reddit-public-json",
                raw={"subreddit": data.get("subreddit"), "score": score, "comments": comments},
            )
        )
    return items


def collect_github(query: str, limit: int, timeout: float) -> list[EvidenceItem]:
    params = urllib.parse.urlencode({"q": query, "sort": "updated", "order": "desc", "per_page": limit})
    url = f"https://api.github.com/search/repositories?{params}"
    status, _, body = http_get(url, timeout=timeout, accept="application/vnd.github+json")
    if status != 200:
        fallback = collect_site_search("github", query, "site:github.com", limit, timeout)
        return fallback or [boundary_item("github", query, url, status, body)]
    payload = json.loads(body)
    items: list[EvidenceItem] = []
    for repo in payload.get("items", [])[:limit]:
        stars = float(repo.get("stargazers_count") or 0)
        forks = float(repo.get("forks_count") or 0)
        items.append(
            EvidenceItem(
                lane="github",
                query=query,
                url=repo.get("html_url") or "",
                title=repo.get("full_name") or "",
                summary=normalize_space(repo.get("description") or ""),
                source_type="primary repository",
                published_at=repo.get("updated_at") or "",
                observed_at=now_iso(),
                metric_score=min(stars, 5000) / 20 + forks / 10,
                route="github-search-api",
                raw={"stars": stars, "forks": forks, "language": repo.get("language")},
            )
        )
    return items


def collect_lane(lane: str, query: str, limit: int, timeout: float) -> list[EvidenceItem]:
    if lane == "web":
        return collect_web(query, limit, timeout)
    if lane == "reddit":
        return collect_reddit(query, limit, timeout)
    if lane == "hn":
        return collect_hn(query, limit, timeout)
    if lane == "github":
        return collect_github(query, limit, timeout)
    if lane == "youtube":
        return collect_site_search("youtube", query, "site:youtube.com/watch OR site:youtu.be", limit, timeout)
    if lane == "x":
        return collect_site_search("x", query, "site:x.com OR site:twitter.com", limit, timeout)
    return collect_site_search(lane, query, f"site:{lane}", limit, timeout)


def boundary_item(lane: str, query: str, url: str, status: int, body: str) -> EvidenceItem:
    return EvidenceItem(
        lane=lane,
        query=query,
        url=url,
        title=f"{lane} access boundary",
        summary=normalize_space(body)[:500],
        source_type="access boundary",
        observed_at=now_iso(),
        access_status=detect_access_status(status, body),
        route="boundary",
        raw={"http_status": status},
    )


def expand_queries(seed: str, rounds: int) -> list[str]:
    queries = [normalize_space(seed)]
    if rounds > 1:
        queries.extend(
            [
                f"{seed} latest",
                f"{seed} trending",
                f"{seed} discussion",
                f"{seed} review OR benchmark OR launch",
            ]
        )
    seen: set[str] = set()
    unique: list[str] = []
    for query in queries:
        key = query.lower()
        if key not in seen:
            seen.add(key)
            unique.append(query)
    return unique


def dedupe_items(items: Iterable[EvidenceItem]) -> list[EvidenceItem]:
    best: dict[str, EvidenceItem] = {}
    for item in items:
        key = canonicalize_url(item.url)
        if not key:
            key = hashlib.sha256(f"{item.lane}|{item.title}".encode("utf-8")).hexdigest()
        current = best.get(key)
        if current is None or item.metric_score > current.metric_score or len(item.summary) > len(current.summary):
            item.url = canonicalize_url(item.url) if item.url.startswith(("http://", "https://")) else item.url
            best[key] = item
    return list(best.values())


def score_items(items: list[EvidenceItem], seed_query: str) -> list[EvidenceItem]:
    terms = {term.lower() for term in re.findall(r"[A-Za-z0-9가-힣]{2,}", seed_query)}
    lane_weights = {
        "web": 1.0,
        "reddit": 1.25,
        "hn": 1.25,
        "github": 1.35,
        "youtube": 1.1,
        "x": 1.2,
    }
    for item in items:
        haystack = f"{item.title} {item.summary}".lower()
        overlap = sum(1 for term in terms if term in haystack)
        recency = recency_score(item.published_at)
        access = 0.0 if item.access_status == "ok" else -2.0
        item.score = round(
            lane_weights.get(item.lane, 1.0) * (overlap * 2.0 + recency + min(item.metric_score, 500) / 50.0)
            + access,
            3,
        )
        if item.access_status != "ok":
            item.confidence = "low"
        elif item.score >= 8:
            item.confidence = "high"
        elif item.score >= 4:
            item.confidence = "medium"
        else:
            item.confidence = "low"
    return sorted(items, key=lambda item: item.score, reverse=True)


def recency_score(value: str) -> float:
    if not value:
        return 0.0
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = dt.datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return 0.0
    age_days = max(0.0, (dt.datetime.now(dt.timezone.utc) - parsed).total_seconds() / 86400)
    if age_days <= 7:
        return 4.0
    if age_days <= 30:
        return 2.5
    if age_days <= 180:
        return 1.0
    return 0.0


def enrich_items(
    items: list[EvidenceItem],
    timeout: float,
    workers: int,
    escalation: str = "public",
    media_metadata: bool = False,
) -> list[EvidenceItem]:
    needs_fetch = [
        item
        for item in items
        if item.access_status == "ok"
        and item.url.startswith(("http://", "https://"))
        and (not item.summary or item.source_type == "web page")
    ]
    if not needs_fetch:
        return items
    by_url = {item.url: item for item in items}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                extract_page,
                item.url,
                item.lane,
                item.query,
                f"{item.route}+page-fetch",
                timeout,
                escalation,
                media_metadata,
            ): item
            for item in needs_fetch
        }
        for future in concurrent.futures.as_completed(futures):
            original = futures[future]
            try:
                enriched = future.result()
            except Exception as exc:
                original.access_status = "fetch failed"
                original.raw["fetch_error"] = f"{type(exc).__name__}: {exc}"
                continue
            merged = by_url.get(original.url, original)
            merged.title = enriched.title or merged.title
            merged.summary = enriched.summary or merged.summary
            merged.published_at = enriched.published_at or merged.published_at
            merged.access_status = enriched.access_status
            merged.raw.update(enriched.raw)
    return items


def run_research(args: argparse.Namespace) -> dict[str, Any]:
    started = now_iso()
    lanes = [lane.strip().lower() for lane in args.lanes.split(",") if lane.strip()]
    queries = expand_queries(args.query, args.rounds)
    collected: list[EvidenceItem] = []
    failures: list[dict[str, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(collect_lane, lane, query, args.limit_per_lane, args.timeout): (lane, query)
            for query in queries
            for lane in lanes
        }
        for future in concurrent.futures.as_completed(futures):
            lane, query = futures[future]
            try:
                collected.extend(future.result())
            except Exception as exc:
                failures.append({"lane": lane, "query": query, "error": f"{type(exc).__name__}: {exc}"})
    items = dedupe_items(collected)
    if args.fetch_pages:
        items = enrich_items(
            items,
            args.timeout,
            args.workers,
            getattr(args, "escalation", "public"),
            getattr(args, "media_metadata", False),
        )
    scored = score_items(items, args.query)
    report_pack = build_report_pack(scored, args.query, lanes, queries, started, failures)
    out_dir = resolve_output_dir(args)
    write_report_pack(out_dir, report_pack)
    return {"out_dir": str(out_dir), "report_pack": report_pack}


def build_claim_ledger(items: list[EvidenceItem]) -> list[dict[str, Any]]:
    ledger: list[dict[str, Any]] = []
    for index, item in enumerate(items[:30], start=1):
        claim = item.title or item.summary[:120] or item.url
        ledger.append(
            {
                "id": f"claim-{index:03d}",
                "claim": claim,
                "status": "source-observed" if item.access_status == "ok" else "access-limited",
                "confidence": item.confidence,
                "evidence_urls": [item.url],
                "source_lane": item.lane,
                "route": item.route,
                "published_at": item.published_at,
                "observed_at": item.observed_at,
                "score": item.score,
                "notes": item.summary,
            }
        )
    return ledger


def build_report_pack(
    items: list[EvidenceItem],
    query: str,
    lanes: list[str],
    queries: list[str],
    started: str,
    failures: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "query": query,
        "started_at": started,
        "finished_at": now_iso(),
        "capabilities": optional_capabilities(),
        "lanes": lanes,
        "queries": queries,
        "failures": failures,
        "evidence": [item.to_dict() for item in items],
        "claim_ledger": build_claim_ledger(items),
        "markdown_report": render_markdown_report(query, lanes, queries, items, failures),
    }


def render_markdown_report(
    query: str, lanes: list[str], queries: list[str], items: list[EvidenceItem], failures: list[dict[str, str]]
) -> str:
    lines = [
        f"# Moonshot Research Report: {query}",
        "",
        f"- Research date: {dt.date.today().isoformat()}",
        f"- Lanes: {', '.join(lanes)}",
        f"- Query variants: {len(queries)}",
        f"- Evidence items after dedupe: {len(items)}",
        "",
        "## Top Evidence",
        "",
    ]
    for index, item in enumerate(items[:20], start=1):
        title = item.title or item.url
        lines.extend(
            [
                f"### {index}. {title}",
                "",
                f"- URL: {item.url}",
                f"- Lane: {item.lane}",
                f"- Type: {item.source_type}",
                f"- Route: {item.route}",
                f"- Published: {item.published_at or 'unknown'}",
                f"- Observed: {item.observed_at}",
                f"- Score: {item.score} ({item.confidence})",
                f"- Access: {item.access_status}",
                f"- Evidence: {item.summary or '(no summary extracted)'}",
                "",
            ]
        )
    if failures:
        lines.extend(["## Lane Failures", ""])
        for failure in failures:
            lines.append(f"- {failure['lane']} / {failure['query']}: {failure['error']}")
        lines.append("")
    lines.extend(
        [
            "## Limits",
            "",
            "- This harness samples public routes; it is not a complete platform firehose.",
            "- Login walls, paywalls, private APIs, and CAPTCHA challenges are access boundaries.",
            "- Treat this report pack as evidence for Codex synthesis, not as a final statistical measurement.",
        ]
    )
    return "\n".join(lines) + "\n"


def resolve_output_dir(args: argparse.Namespace) -> Path:
    if args.out:
        out_dir = Path(args.out)
    else:
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        slug = re.sub(r"[^a-zA-Z0-9가-힣]+", "-", args.query).strip("-")[:48] or "research"
        skill_dir = Path(__file__).resolve().parents[1]
        out_dir = skill_dir / "output" / "research" / f"{stamp}-{slug}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def write_report_pack(out_dir: Path, pack: dict[str, Any]) -> None:
    (out_dir / "evidence.json").write_text(
        json.dumps(pack["evidence"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "claim-ledger.json").write_text(
        json.dumps(pack["claim_ledger"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary = {key: value for key, value in pack.items() if key not in {"evidence", "claim_ledger", "markdown_report"}}
    (out_dir / "run.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(pack["markdown_report"], encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a public-web research fan-out and write evidence/report artifacts.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("query", nargs="?", help="Research question or topic")
    parser.add_argument("--lanes", default=",".join(DEFAULT_LANES), help="Comma-separated lanes")
    parser.add_argument("--rounds", type=int, default=2, help="Query expansion rounds")
    parser.add_argument("--limit-per-lane", type=int, default=5, help="Max results per lane/query")
    parser.add_argument("--workers", type=int, default=8, help="Parallel worker count")
    parser.add_argument("--timeout", type=float, default=12.0, help="Network timeout seconds")
    parser.add_argument("--out", help="Output directory")
    parser.add_argument("--no-fetch-pages", action="store_false", dest="fetch_pages", help="Skip page enrichment fetches")
    parser.add_argument(
        "--escalation",
        default="public",
        choices=ESCALATION_LEVELS,
        help="Fetch escalation: basic urllib, public URL variants, optional TLS, optional browser, or full",
    )
    parser.add_argument("--media-metadata", action="store_true", help="Use optional yt-dlp metadata for media URLs")
    parser.add_argument("--print-capabilities", action="store_true", help="Print optional dependency capabilities and exit")
    parser.set_defaults(fetch_pages=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.print_capabilities:
        print(json.dumps(optional_capabilities(), ensure_ascii=False, indent=2))
        return 0
    if not args.query:
        parser.error("query is required unless --print-capabilities is used")
    if args.rounds < 1:
        parser.error("--rounds must be >= 1")
    if args.limit_per_lane < 1:
        parser.error("--limit-per-lane must be >= 1")
    result = run_research(args)
    print(f"Moonshot research artifacts written to: {result['out_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
