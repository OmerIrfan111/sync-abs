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

# Domains known to serve real, authentic supplier-hosted product photos
# (not just "a web result about this product"). A hit from one of these is
# about as authoritative as an image gets for an exact SKU/UPC match, so
# these are boosted to the top of search_by_upc()'s results.
TRUSTED_SUPPLIER_DOMAINS = (
    "officedepot.com", "media.officedepot.com",
    "static.storeautomator.com", "storeautomator.com",
    "cdwg.com", "cdn.cdwg.com",
    "ingram.com", "assets.ingrammicro.com", "ingrammicro.com",
)

# Generic English words that would otherwise count as a real "match" between
# a query and a candidate's title, defeating the relevance filter below.
_RELEVANCE_STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "this", "that", "your", "best",
    "new", "set", "pack", "kit", "pro", "plus", "inch", "black", "white",
})


def _is_relevant(query: str, candidate_title: str, candidate_purl: str) -> bool:
    """
    Real incident (2026-10-09): Bing Image Search, for narrow/obscure B2B
    product titles it has little real indexed content for, returns images
    with zero topical connection to the query at all — live-confirmed: a
    search for "HDMI TO VGA M/F DONGLE C2G" returned 12/12 results that were
    every one about the actor Irrfan Khan, not a glitch or a bot-block
    (generic queries like "apple iphone" return genuinely relevant results
    from the same endpoint). There was previously no relevance check
    anywhere on this path — whatever Bing ranked first was shown directly
    as a "product photo" candidate.

    This requires at least one real token (length >= 3, not a generic
    stopword) shared between the query and the candidate's own title/page
    URL — cheap, honest, and directly verified against the real Irrfan Khan
    response above (0/12 pass; none share any token with the query).
    """
    import re

    query_tokens = {
        t.lower() for t in re.findall(r"[A-Za-z0-9]{3,}", query or "")
        if t.lower() not in _RELEVANCE_STOPWORDS
    }
    if not query_tokens:
        return True
    haystack = f"{candidate_title or ''} {candidate_purl or ''}".lower()
    return any(tok in haystack for tok in query_tokens)


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

    def search_web_images(self, query: str, max_results: int = 35) -> List[ImageCandidate]:
        """
        max_results default raised 2026-10-10: a single Bing results page
        (one HTTP request, already being made regardless) naturally yields
        ~35 raw result tiles — the old default of 12 discarded roughly
        two-thirds of what was already downloaded for free, which is the
        real reason the manual photo picker showed noticeably fewer options
        than searching bing.com directly in a browser (confirmed by the
        user, and by live-testing: 35 raw matches for the same query, only
        2 rejected by the relevance filter, but the result was being capped
        at 12 before this reached the caller).
        """
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

        # Transient network failures (DNS blips, momentary connection resets)
        # must not be swallowed as "zero results" — that silently starves the
        # whole UPC image-match pipeline for products caught in the blip, and
        # worse, the outer caller's own retry/backoff (see
        # ImageMatchingService._fetch_candidates_with_backoff) never fires
        # because search_by_upc() never raises. Retry here, at the network
        # call itself, before giving up.
        page_html = None
        last_exc: Optional[Exception] = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    page_html = resp.read().decode("utf-8", errors="ignore")
                break
            except Exception as exc:
                last_exc = exc
                if attempt < 2:
                    time.sleep(0.4 * (2 ** attempt))

        if page_html is None:
            logger.warning(f"Bing web image search failed for '{clean_q}' after retries: {last_exc}")
            return []

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

                # Real relevance check (see _is_relevant docstring) — Bing
                # returning topically unrelated images for narrow queries is
                # a genuine, confirmed behavior, not an edge case to ignore.
                if not _is_relevant(clean_q, title, purl):
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

        return candidates

    def search_by_upc(
        self,
        upc: str,
        title: Optional[str] = None,
        brand: Optional[str] = None,
        mpn: Optional[str] = None,
        **kwargs
    ) -> List[ImageCandidate]:
        """
        Gathers candidates from multiple query strategies and MERGES them
        (rather than stopping at the first non-empty result), with
        brand-anchored combined queries trusted for any hit, and raw-UPC-only
        hits trusted ONLY when they come from a known supplier CDN.

        Rationale: a pure barcode ("just the UPC") search is a two-edged
        strategy. UPC/EAN barcodes get reused/collide across completely
        unrelated products in various regional/retail registries far more
        than people expect (electronics part found alongside perfume,
        shampoo, car parts for the exact same code) — so a raw-UPC-alone hit
        on a random retailer page is NOT a reliable signal, and showing it as
        a suggestion actively misleads. It's only trustworthy when it comes
        from a TRUSTED_SUPPLIER_DOMAINS CDN, since that's the actual supplier
        hosting a photo under this SKU/UPC, not a web search guessing. Brand
        (and brand+MPN/title) narrow enough that collisions are rare, so
        those tiers' results are trusted outright.
        """
        import re

        clean_upc = (upc or "").strip()
        all_candidates: List[ImageCandidate] = []
        seen_urls: set = set()

        def add_results(results: List[ImageCandidate], trusted_domain_only: bool = False):
            for r in results:
                if trusted_domain_only and not any(d in r.image_url.lower() for d in TRUSTED_SUPPLIER_DOMAINS):
                    continue
                if r.image_url not in seen_urls:
                    seen_urls.add(r.image_url)
                    all_candidates.append(r)

        # Raised from 12/10 (2026-10-10) alongside search_web_images' own
        # default — each tier is one Bing page already being fetched in
        # full, so capping well below what it actually returns just throws
        # away real candidates for free.
        target = 30

        # Tier 1: raw UPC alone — collision-prone, so only trust hits that
        # land on a known supplier's own CDN (a real, independent signal);
        # discard anything else rather than showing unrelated products.
        if clean_upc:
            add_results(self.search_web_images(clean_upc, max_results=30), trusted_domain_only=True)

        # Tier 2: UPC + Brand — still UPC-anchored, narrows by brand.
        if clean_upc and brand and len(all_candidates) < target:
            add_results(self.search_web_images(f"{clean_upc} {brand}".strip(), max_results=30))

        # Tier 3: UPC + Brand + MPN/title — most specific, but can be too
        # narrow for how some products are actually indexed on the web.
        if clean_upc and brand and mpn and len(all_candidates) < target:
            add_results(self.search_web_images(f"{clean_upc} {brand} {mpn}".strip(), max_results=30))
        elif clean_upc and brand and title and len(all_candidates) < target:
            clean_title = re.sub(r'[^a-zA-Z0-9\s-]', ' ', title).split()
            clean_str = " ".join(clean_title[:5])
            add_results(self.search_web_images(f"{clean_upc} {brand} {clean_str}".strip(), max_results=30))

        # Tier 4 (fallback, no UPC anchor): Brand + MPN alone. Only used to
        # top up the pool when UPC-anchored tiers found little or nothing.
        if brand and mpn and len(all_candidates) < 5:
            add_results(self.search_web_images(f"{brand} {mpn}".strip(), max_results=30))

        # Raw UPC search can surface unrelated products for a UPC that's
        # ambiguous/reused in some barcode registries (a real, common data
        # issue — not something a search query can fully avoid), but it also
        # sometimes finds a known supplier's own CDN-hosted photo for this
        # exact part. A trusted-supplier-domain hit is about as authoritative
        # as it gets, so promote those to the front — stable sort, doesn't
        # reorder within either group.
        all_candidates.sort(
            key=lambda c: 0 if any(d in c.image_url.lower() for d in TRUSTED_SUPPLIER_DOMAINS) else 1
        )

        return all_candidates


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
        # A transient failure must raise, not return [], so the outer
        # backoff retry actually fires instead of being defeated by a
        # result indistinguishable from "no results".
        try:
            with urllib.request.urlopen(url, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.error(f"Google custom search failed for UPC {upc}: {exc}")
            raise

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


class BingImageSearchAPIProvider(ImageSearchProvider):
    """
    The real, official Bing Image Search API (Azure Cognitive Services /
    Bing Search v7) — the same underlying Bing index a real browser sees,
    fetched through Bing's own sanctioned endpoint rather than scraping
    bing.com's HTML. Added 2026-10-10 after live-confirming that
    BingWebImageSearchProvider's scrape is subject to an anti-scraping
    countermeasure: the exact same narrow B2B query sent 3 times in a row
    returned 3 different, completely unrelated results each time (random
    decoy content), while the same query typed into a real browser returned
    consistent, correct results every time. No query tuning fixes this —
    the scraped endpoint simply never receives Bing's real ranked results
    for this traffic pattern. This provider does, because it's not scraped.

    Requires a real Azure/Bing Search subscription key
    (BING_IMAGE_SEARCH_API_KEY, falls back to IMAGE_SEARCH_API_KEY).
    """

    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        self.api_key = api_key or settings.BING_IMAGE_SEARCH_API_KEY or settings.IMAGE_SEARCH_API_KEY
        self.endpoint = endpoint or settings.BING_IMAGE_SEARCH_ENDPOINT

    def _call(self, query: str, count: int) -> Dict[str, Any]:
        import urllib.parse
        params = urllib.parse.urlencode({"q": query, "count": count, "safeSearch": "Moderate"})
        url = f"{self.endpoint}?{params}"
        req = urllib.request.Request(url, headers={"Ocp-Apim-Subscription-Key": self.api_key})
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _to_candidates(self, data: Dict[str, Any], query: str, max_results: int) -> List[ImageCandidate]:
        candidates = []
        for item in data.get("value", []):
            img_url = item.get("contentUrl")
            t = item.get("name", "")
            host_url = item.get("hostPageUrl", "")
            if not img_url:
                continue
            # Belt-and-suspenders: the official API shouldn't need this the
            # way the scraper did, but costs nothing to keep the same
            # real-incident relevance guard applied everywhere.
            if not _is_relevant(query, t, host_url):
                continue
            candidates.append(ImageCandidate(image_url=img_url, title=t, source="bing_api", snippet=host_url))
            if len(candidates) >= max_results:
                break
        return candidates

    def search_web_images(self, query: str, max_results: int = 35) -> List[ImageCandidate]:
        if not self.api_key or not query or not query.strip():
            return []
        try:
            data = self._call(query.strip(), count=max_results)
        except Exception as exc:
            logger.warning(f"Bing Image Search API failed for '{query}': {exc}")
            return []
        return self._to_candidates(data, query, max_results)

    def search_by_upc(
        self,
        upc: str,
        title: Optional[str] = None,
        brand: Optional[str] = None,
        mpn: Optional[str] = None,
        **kwargs
    ) -> List[ImageCandidate]:
        if not self.api_key:
            logger.warning("Bing Image Search API key not configured; falling back to empty candidates")
            return []
        query = f"{upc} {brand or ''} {mpn or ''}".strip()
        # A transient failure must raise, not return [] — same reasoning as
        # the other real providers: an empty list here is indistinguishable
        # from "no results" and never triggers the outer backoff retry.
        try:
            data = self._call(query, count=30)
        except Exception as exc:
            logger.error(f"Bing Image Search API failed for UPC {upc}: {exc}")
            raise
        return self._to_candidates(data, query, 30)


def get_image_search_provider(provider_name: Optional[str] = None) -> ImageSearchProvider:
    provider = (provider_name or settings.IMAGE_SEARCH_PROVIDER or "bing").lower()
    if provider in ("bing_api", "bingapi", "azure"):
        return BingImageSearchAPIProvider()
    if provider in ("google", "customsearch"):
        return GoogleCustomSearchProvider()
    elif provider in ("mock", "test"):
        return MockImageSearchProvider()
    return BingWebImageSearchProvider()
