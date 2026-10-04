import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import urllib.request
import urllib.error
import json
from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class ImageCandidate:
    image_url: str
    title: str
    brand: Optional[str] = None
    source: str = "web_search"
    snippet: Optional[str] = None


class ImageSearchProvider(ABC):
    @abstractmethod
    def search_by_upc(
        self,
        upc: str,
        title: Optional[str] = None,
        brand: Optional[str] = None,
        mpn: Optional[str] = None,
        **kwargs
    ) -> List[ImageCandidate]:
        """Searches image candidates using a UPC barcode string and optional product metadata."""
        pass


class MockImageSearchProvider(ImageSearchProvider):
    """
    Mock image search provider for deterministic testing and offline sandbox execution.
    Can be seeded with specific candidate responses.
    """
    _seeded_candidates: Dict[str, List[Dict[str, Any]]] = {}

    @classmethod
    def seed_upc_result(cls, upc: str, candidates: List[Dict[str, Any]]):
        cls._seeded_candidates[upc] = candidates
        try:
            from app.core.upc_utils import normalize_upc
            norm = normalize_upc(upc)
            cls._seeded_candidates[norm] = candidates
        except Exception:
            pass

    @classmethod
    def clear_seeds(cls):
        cls._seeded_candidates.clear()

    def search_by_upc(
        self,
        upc: str,
        title: Optional[str] = None,
        brand: Optional[str] = None,
        mpn: Optional[str] = None,
        **kwargs
    ) -> List[ImageCandidate]:
        candidates_raw = self._seeded_candidates.get(upc)
        if candidates_raw is None:
            try:
                from app.core.upc_utils import normalize_upc
                norm = normalize_upc(upc)
                candidates_raw = self._seeded_candidates.get(norm)
            except Exception:
                pass

        if candidates_raw is not None:
            return [
                ImageCandidate(
                    image_url=c["image_url"],
                    title=c["title"],
                    brand=c.get("brand"),
                    source=c.get("source", "mock_search"),
                    snippet=c.get("snippet")
                )
                for c in candidates_raw
            ]
        # Default mock candidate
        return [
            ImageCandidate(
                image_url=f"https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format",
                title="Generic Computer Accessory",
                brand="Generic",
                source="mock_search"
            )
        ]


class BingWebImageSearchProvider(ImageSearchProvider):
    """
    Scrapes high-resolution real product images via Bing Image Search.
    Does not require a paid API key and works for B2B & consumer products.
    """
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def search_web_images(self, query: str, max_results: int = 12) -> List[ImageCandidate]:
        import html
        import re
        import urllib.parse

        if not query or not query.strip():
            return []

        clean_q = query.strip()
        encoded = urllib.parse.quote(clean_q)
        url = f"https://www.bing.com/images/search?q={encoded}&form=HDRSC2&first=1"
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        req = urllib.request.Request(url, headers=headers)

        candidates: List[ImageCandidate] = []
        seen_urls = set()

        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                page_html = resp.read().decode("utf-8", errors="ignore")

            pattern = re.compile(r'class="iusc"[^>]*?m="([^"]+)"', re.DOTALL)
            for match in pattern.finditer(page_html):
                raw_m = match.group(1)
                try:
                    unescaped = html.unescape(raw_m)
                    data = json.loads(unescaped)
                    murl = data.get("murl")
                    title = data.get("t") or data.get("desc") or ""
                    purl = data.get("purl") or ""

                    if not murl or not murl.startswith("http") or murl in seen_urls:
                        continue

                    # Filter obvious bad patterns
                    bad_patterns = ["placeholder", "no_image", "noimage", "blank.", "pixel.gif"]
                    if any(b in murl.lower() for b in bad_patterns):
                        continue

                    seen_urls.add(murl)
                    candidates.append(
                        ImageCandidate(
                            image_url=murl,
                            title=title,
                            source="bing_images",
                            snippet=purl
                        )
                    )
                    if len(candidates) >= max_results:
                        break
                except Exception:
                    continue

        except Exception as exc:
            logger.warning(f"Bing web image search failed for '{clean_q}': {exc}")

        return candidates

    def search_by_upc(
        self,
        upc: str,
        title: Optional[str] = None,
        brand: Optional[str] = None,
        mpn: Optional[str] = None,
        **kwargs
    ) -> List[ImageCandidate]:
        import re

        clean_upc = (upc or "").strip()
        queries_to_try = []

        # Strategy 1: Specific query with UPC + Brand + MPN
        if clean_upc and brand and mpn:
            queries_to_try.append(f"{clean_upc} {brand} {mpn}".strip())
        elif clean_upc and brand and title:
            clean_title = re.sub(r'[^a-zA-Z0-9\s-]', ' ', title).split()
            clean_str = " ".join(clean_title[:5])
            queries_to_try.append(f"{clean_upc} {brand} {clean_str}".strip())

        # Strategy 2: Brand + MPN (even without UPC)
        if brand and mpn:
            queries_to_try.append(f"{brand} {mpn}".strip())

        # Strategy 3: UPC + Brand
        if clean_upc and brand:
            queries_to_try.append(f"{clean_upc} {brand}".strip())

        # Strategy 4: Raw UPC
        if clean_upc:
            queries_to_try.append(clean_upc)

        for q in queries_to_try:
            results = self.search_web_images(q, max_results=10)
            if results:
                return results

        return []


class SerperImageSearchProvider(ImageSearchProvider):
    """Integrates with Serper.dev Google Images Search API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.IMAGE_SEARCH_API_KEY

    def search_by_upc(
        self,
        upc: str,
        title: Optional[str] = None,
        brand: Optional[str] = None,
        mpn: Optional[str] = None,
        **kwargs
    ) -> List[ImageCandidate]:
        if not self.api_key:
            logger.warning("Serper API key not configured; falling back to empty candidates")
            return []

        url = "https://google.serper.dev/images"
        query = f"{upc} {brand or ''} {mpn or ''}".strip()
        payload = json.dumps({"q": query, "num": 10}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                images = data.get("images", [])
                candidates = []
                for img in images:
                    img_url = img.get("imageUrl")
                    t = img.get("title", "")
                    if img_url:
                        candidates.append(ImageCandidate(
                            image_url=img_url,
                            title=t,
                            source="serper_google"
                        ))
                return candidates
        except Exception as exc:
            logger.error(f"Serper image search failed for UPC {upc}: {exc}")
            return []


class GoogleCustomSearchProvider(ImageSearchProvider):
    """Integrates with Google Custom Search JSON API."""

    def __init__(self, api_key: Optional[str] = None, cx: Optional[str] = None):
        self.api_key = api_key or settings.IMAGE_SEARCH_API_KEY
        self.cx = cx or "partner-cx"

    def search_by_upc(
        self,
        upc: str,
        title: Optional[str] = None,
        brand: Optional[str] = None,
        mpn: Optional[str] = None,
        **kwargs
    ) -> List[ImageCandidate]:
        if not self.api_key:
            return []

        import urllib.parse
        q_str = f"{upc} {brand or ''} {mpn or ''}".strip()
        query = urllib.parse.quote(q_str)
        url = f"https://www.googleapis.com/customsearch/v1?q={query}&searchType=image&key={self.api_key}&cx={self.cx}&num=10"
        try:
            with urllib.request.urlopen(url, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("items", [])
                candidates = []
                for it in items:
                    img_url = it.get("link")
                    t = it.get("title", "")
                    if img_url:
                        candidates.append(ImageCandidate(
                            image_url=img_url,
                            title=t,
                            source="google_custom_search"
                        ))
                return candidates
        except Exception as exc:
            logger.error(f"Google custom search failed for UPC {upc}: {exc}")
            return []


def get_image_search_provider(provider_name: Optional[str] = None) -> ImageSearchProvider:
    provider = (provider_name or settings.IMAGE_SEARCH_PROVIDER or "bing").lower()
    if provider == "serper":
        return SerperImageSearchProvider()
    elif provider in ("google", "customsearch"):
        return GoogleCustomSearchProvider()
    elif provider in ("mock", "test"):
        return MockImageSearchProvider()
    return BingWebImageSearchProvider()
