from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
}

JS_IMPORT_RE = re.compile(r"(?:import\s+(?:[^'\"]+from\s+)?|import\()\s*['\"]([^'\"]+)['\"]")
SOURCE_MAP_RE = re.compile(r"sourceMappingURL\s*=\s*([^\s*]+)")
FETCH_HINT_RE = re.compile(r"(?:fetch|axios\.(?:get|post|put|delete|patch))\s*\(\s*['\"]([^'\"]+)['\"]")


@dataclass
class CrawlResult:
    url: str
    status_code: int | None
    content_type: str | None
    local_path: str | None
    kind: str
    discovered_links: list[str] = field(default_factory=list)
    sources: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class MirrorCrawler:
    def __init__(
        self,
        base_url: str,
        result_dir: Path,
        max_pages: int = 200,
        scope: str = "same-origin",
        include_assets: set[str] | None = None,
        respect_robots: bool = False,
        max_depth: int = 3,
        concurrency: int = 10,
        rate_rps: float = 5.0,
        rewrite_links: bool = True,
        store_raw: bool = False,
    ) -> None:
        self.base_url = self._normalize_url(base_url)
        self.base = urlparse(self.base_url)
        self.result_dir = result_dir
        self.max_pages = max_pages
        self.scope = scope
        self.include_assets = include_assets or {"js", "css", "img", "font"}
        self.respect_robots = respect_robots
        self.max_depth = max_depth
        self.concurrency = max(1, concurrency)
        self.rate_interval = 1.0 / max(0.1, rate_rps)
        self.rewrite_links = rewrite_links
        self.store_raw = store_raw

        self.host_root = self.result_dir / "mirror" / self.base.netloc
        self.meta_dir = self.host_root / "_meta"
        self.pages_dir = self.host_root / "pages"
        self.assets_dir = self.host_root / "assets"
        self.raw_dir = self.host_root / "raw"

        self.seen: set[str] = set()
        self.local_map: dict[str, Path] = {}
        self.asset_count = 0
        self.page_count = 0
        self.start_time = time.time()
        self._rate_lock = asyncio.Lock()
        self._last_fetch_ts = 0.0

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = f"https://{url}"
            parsed = urlparse(url)
        query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS]
        normalized = parsed._replace(fragment="", query=urlencode(query))
        path = normalized.path or "/"
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        normalized = normalized._replace(path=path)
        return urlunparse(normalized)

    def _in_scope(self, url: str) -> bool:
        p = urlparse(url)
        if p.scheme in {"mailto", "tel", "javascript", "data"}:
            return False
        if self.scope == "same-origin":
            return (p.scheme, p.netloc) == (self.base.scheme, self.base.netloc)
        if self.scope == "same-host":
            return p.netloc == self.base.netloc
        return True

    def _ensure_dirs(self) -> None:
        for p in [self.meta_dir, self.pages_dir, self.assets_dir]:
            p.mkdir(parents=True, exist_ok=True)
        if self.store_raw:
            self.raw_dir.mkdir(parents=True, exist_ok=True)

    def _classify_asset(self, content_type: str | None, path: str) -> str:
        ctype = (content_type or "").lower()
        path_l = path.lower()
        if "javascript" in ctype or path_l.endswith((".js", ".mjs", ".cjs")):
            return "js"
        if "css" in ctype or path_l.endswith(".css"):
            return "css"
        if any(x in ctype for x in ["font", "woff", "ttf"]) or path_l.endswith((".woff", ".woff2", ".ttf", ".otf")):
            return "font"
        if any(x in ctype for x in ["image", "svg"]) or path_l.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico")):
            return "img"
        return "misc"

    def _url_to_local_path(self, url: str, kind: str, content_type: str | None = None) -> Path:
        p = urlparse(url)
        raw_path = p.path or "/"
        if kind == "page":
            page_rel = raw_path.lstrip("/")
            if not page_rel:
                page_rel = "index"
            if raw_path.endswith("/") or "." not in Path(page_rel).name:
                page_rel = f"{page_rel.rstrip('/')}/index.html"
            return self.pages_dir / page_rel

        asset_kind = self._classify_asset(content_type, raw_path)
        rel = raw_path.lstrip("/") or "asset"
        if rel.endswith("/"):
            rel += "index"
        name = Path(rel).name
        if "." not in name:
            ext = {
                "js": ".js",
                "css": ".css",
                "img": ".bin",
                "font": ".bin",
                "misc": ".bin",
            }[asset_kind]
            rel = f"{rel}{ext}"

        if p.query:
            digest = hashlib.sha1(p.query.encode("utf-8")).hexdigest()[:8]
            rp = Path(rel)
            rel = str(rp.with_name(f"{rp.stem}.{digest}{rp.suffix}"))

        return self.assets_dir / asset_kind / rel

    def _extract_js_sources(self, js_text: str) -> dict[str, list[str]]:
        maps = [m.strip().rstrip("*/") for m in SOURCE_MAP_RE.findall(js_text)]
        imports = JS_IMPORT_RE.findall(js_text)
        hints = FETCH_HINT_RE.findall(js_text)
        return {
            "source_maps": sorted(set(maps)),
            "imports": sorted(set(imports)),
            "network_hints": sorted(set(hints)),
        }

    def _extract_html_data(self, url: str, html: str) -> tuple[list[str], dict[str, Any], str]:
        soup = BeautifulSoup(html, "html.parser")
        found: list[str] = []

        def push(link: str | None) -> None:
            if not link:
                return
            abs_url = self._normalize_url(urljoin(url, link))
            if self._in_scope(abs_url):
                found.append(abs_url)

        for tag in soup.select("a[href]"):
            push(tag.get("href"))
        for tag in soup.select("script[src]"):
            push(tag.get("src"))
        for tag in soup.select("link[rel]"):
            rel = " ".join(tag.get("rel", []))
            if "stylesheet" in rel or "preload" in rel:
                push(tag.get("href"))
        for tag in soup.select("img[src], source[srcset]"):
            if tag.get("src"):
                push(tag.get("src"))
            if tag.get("srcset"):
                for part in tag.get("srcset", "").split(","):
                    push(part.strip().split(" ")[0])

        forms = []
        for form in soup.select("form"):
            inputs = []
            for inp in form.select("input, textarea, select"):
                inputs.append({"name": inp.get("name"), "type": inp.get("type", inp.name)})
            forms.append({
                "action": urljoin(url, form.get("action", "")) if form.get("action") else None,
                "method": (form.get("method") or "get").lower(),
                "inputs": inputs,
            })

        inline_scripts = [script.get_text() for script in soup.select("script:not([src])") if script.get_text(strip=True)]
        inline_meta = [self._extract_js_sources(text) for text in inline_scripts]
        external_scripts = [self._normalize_url(urljoin(url, s.get("src"))) for s in soup.select("script[src]") if s.get("src")]

        if self.rewrite_links:
            for tag, attr in [
                ("a", "href"),
                ("script", "src"),
                ("link", "href"),
                ("img", "src"),
            ]:
                for node in soup.select(f"{tag}[{attr}]"):
                    old = self._normalize_url(urljoin(url, node.get(attr)))
                    local = self.local_map.get(old)
                    if local:
                        node[attr] = self._relative_ref_for_page(url, local)

        return sorted(set(found)), {
            "inline_scripts": inline_meta,
            "external_script_urls": external_scripts,
            "forms": forms,
        }, str(soup)

    def _relative_ref_for_page(self, page_url: str, target_local: Path) -> str:
        page_local = self.local_map.get(page_url)
        if not page_local:
            return str(target_local)
        return str(Path("..") / Path(target_local).relative_to(self.host_root))

    async def _throttle(self) -> None:
        async with self._rate_lock:
            now = time.time()
            wait = self._last_fetch_ts + self.rate_interval - now
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_fetch_ts = time.time()

    async def _fetch_with_retry(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        for i in range(3):
            await self._throttle()
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code not in {429, 500, 502, 503, 504}:
                return resp
            if i < 2:
                await asyncio.sleep(2**i)
        return resp

    async def crawl(self) -> dict[str, Any]:
        self._ensure_dirs()
        queue = deque([(self.base_url, 0, "page")])
        crawl_log = self.meta_dir / "crawl.jsonl"
        err_log = self.meta_dir / "errors.jsonl"

        async with httpx.AsyncClient(
            timeout=20,
            headers={"User-Agent": "wapper/0.1 (+mirror)", "Accept-Encoding": "gzip, br"},
        ) as client:
            while queue and self.page_count < self.max_pages:
                batch = []
                while queue and len(batch) < self.concurrency:
                    candidate, depth, kind = queue.popleft()
                    if candidate in self.seen:
                        continue
                    if not self._in_scope(candidate):
                        continue
                    self.seen.add(candidate)
                    batch.append((candidate, depth, kind))

                if not batch:
                    continue

                results = await asyncio.gather(*(self._process_one(client, u, d, k) for u, d, k in batch))
                with crawl_log.open("a", encoding="utf-8") as cf, err_log.open("a", encoding="utf-8") as ef:
                    for item, (url, depth, _) in zip(results, batch):
                        cf.write(json.dumps(item.__dict__, ensure_ascii=False) + "\n")
                        if item.error:
                            ef.write(json.dumps(item.__dict__, ensure_ascii=False) + "\n")
                        for link in item.discovered_links:
                            if depth + 1 <= self.max_depth and link not in self.seen:
                                lkind = "page" if self._looks_like_page(link) else "asset"
                                if lkind == "asset":
                                    asset_kind = self._classify_asset(None, urlparse(link).path)
                                    if asset_kind not in self.include_assets:
                                        continue
                                queue.append((link, depth + 1, lkind))

        summary = {
            "base_url": self.base_url,
            "scope": self.scope,
            "max_pages": self.max_pages,
            "visited": len(self.seen),
            "saved_pages": self.page_count,
            "saved_assets": self.asset_count,
            "duration_seconds": round(time.time() - self.start_time, 2),
            "output_root": str(self.host_root),
        }
        (self.meta_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    def _looks_like_page(self, url: str) -> bool:
        path = urlparse(url).path.lower()
        if path.endswith("/") or not Path(path).suffix:
            return True
        return Path(path).suffix in {".html", ".htm", ".php", ".asp", ".aspx", ".jsp"}

    async def _process_one(self, client: httpx.AsyncClient, url: str, depth: int, kind: str) -> CrawlResult:
        del depth
        try:
            response = await self._fetch_with_retry(client, url)
            content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
            body = response.content
            if len(body) > 10 * 1024 * 1024:
                return CrawlResult(url=url, status_code=response.status_code, content_type=content_type, local_path=None, kind=kind, error="response too large")

            is_html = "text/html" in content_type or self._looks_like_page(url)
            eff_kind = "page" if is_html else kind
            local_path = self._url_to_local_path(url, eff_kind, content_type)
            local_path.parent.mkdir(parents=True, exist_ok=True)

            discovered: list[str] = []
            sources: dict[str, Any] = {}
            if is_html:
                text = response.text
                discovered, html_sources, rendered = self._extract_html_data(url, text)
                local_path.write_text(rendered if self.rewrite_links else text, encoding="utf-8", errors="ignore")
                sources.update(html_sources)
                self.page_count += 1
            else:
                local_path.write_bytes(body)
                if "javascript" in content_type or local_path.suffix == ".js":
                    text = body.decode("utf-8", errors="ignore")
                    js_sources = self._extract_js_sources(text)
                    sources.update(js_sources)
                    for hint in js_sources["imports"] + js_sources["source_maps"]:
                        abs_hint = self._normalize_url(urljoin(url, hint))
                        if self._in_scope(abs_hint):
                            discovered.append(abs_hint)
                self.asset_count += 1

            self.local_map[url] = local_path

            if self.store_raw:
                raw_name = hashlib.sha1(url.encode("utf-8")).hexdigest() + ".bin"
                (self.raw_dir / raw_name).write_bytes(body)

            return CrawlResult(
                url=url,
                status_code=response.status_code,
                content_type=content_type,
                local_path=str(local_path.relative_to(self.host_root)),
                kind=eff_kind,
                discovered_links=sorted(set(discovered)),
                sources=sources,
                error=None if response.is_success else f"HTTP {response.status_code}",
            )
        except Exception as exc:  # noqa: BLE001
            return CrawlResult(
                url=url,
                status_code=None,
                content_type=None,
                local_path=None,
                kind=kind,
                error=str(exc),
            )
