import base64
import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Distributor brand strings that don't match the manufacturer's own name in
# Icecat. Anything not listed falls through to generic suffix stripping.
BRAND_OVERRIDES = {
    "hp i": "HP",
    "hp inc": "HP",
    "cisco systems": "Cisco",
    "lg commercial": "LG",
    "apc by schneider electric": "APC",
    "hpe aruba": "Aruba",
    "samsungoem": "Samsung",
    "canon usa": "Canon",
    "vertiv corp": "Vertiv",
    "supermicro": "Supermicro",
}

_TRAILING_NOISE = {"inc", "inc.", "corp", "corp.", "corporation", "llc", "ltd", "usa", "oem", "i", "co", "company", "systems"}

_NOT_FOUND_CODES = (400, 404)
MAX_IMAGES = 6
MAX_BRAND_VARIANTS = 4


@dataclass
class ContentMatch:
    images: List[str]
    title: Optional[str]
    icecat_id: Optional[str]
    matched_by: str
    brand_used: Optional[str] = None
    # full-size URL -> small (~500px, 14-70 KB) rendition for lists and
    # previews. The originals are ~1 MB each (3000x2400): 50 of them in a
    # catalog page never finish loading into 48px thumbnails.
    thumbs: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)


def brand_candidates(brand: Optional[str]) -> List[str]:
    """Ordered, de-duplicated brand spellings to try against Icecat."""
    raw = (brand or "").strip()
    if not raw:
        return []
    out: List[str] = []

    def add(value: Optional[str]):
        value = (value or "").strip()
        if len(value) >= 2 and value.lower() not in {o.lower() for o in out}:
            out.append(value)

    override = BRAND_OVERRIDES.get(raw.lower())
    if override:
        add(override)
    add(raw)

    tokens = re.sub(r"[^\w\s&.\-]", " ", raw).split()
    while tokens and tokens[-1].lower() in _TRAILING_NOISE:
        tokens = tokens[:-1]
    if tokens:
        add(" ".join(tokens))
        add(tokens[0])
    return out[:MAX_BRAND_VARIANTS]


class IcecatContentError(Exception):
    """Transient failure (network, rate limit, 5xx). The product was NOT
    checked; the caller must not record it as a definitive miss."""


class IcecatRestricted(Exception):
    """HTTP 403: the product exists in Icecat but its content is only released
    to Full Icecat accounts (app_key). Definitive for the current account, and
    resolved by configuring ICECAT_APP_KEY, not by retrying."""


class IcecatContentProvider:
    """
    Manufacturer-verified product photos from Icecat, looked up by exact
    GTIN or Brand + manufacturer part number. Exact-identifier lookup means a
    hit is the right product by construction; there is no similarity guessing
    and no search quota, unlike scraped web image search.

    Free Open Icecat covers sponsor brands only; a full Icecat subscription
    (ICECAT_USERNAME/ICECAT_PASSWORD) widens coverage with no code change.
    """

    API_URL = "https://live.icecat.biz/api"

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None, language: str = "en"):
        self.username = username or getattr(settings, "ICECAT_USERNAME", None) or "openIcecat-live"
        self.password = password or getattr(settings, "ICECAT_PASSWORD", None) or ""
        self.app_key = getattr(settings, "ICECAT_APP_KEY", None) or ""
        self.language = language

    def _get(self, params: dict, timeout: float = 15.0, retries: int = 3) -> Optional[dict]:
        query = {"UserName": self.username, "Language": self.language, **params}
        if self.app_key:
            query["app_key"] = self.app_key
        url = f"{self.API_URL}?{urllib.parse.urlencode(query)}"
        headers = {"User-Agent": "SyncABS-ContentSync/1.0", "Accept": "application/json"}
        if self.password:
            token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {token}"
        last: Optional[Exception] = None
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code in _NOT_FOUND_CODES:
                    return None
                if exc.code == 403:
                    raise IcecatRestricted("Full Icecat account required for this product") from exc
                last = exc
                if exc.code in (429, 500, 502, 503, 504):
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                raise IcecatContentError(f"Icecat HTTP {exc.code}") from exc
            except Exception as exc:
                last = exc
                time.sleep(0.5 * (2 ** attempt))
        raise IcecatContentError(f"Icecat unreachable: {last}")

    @staticmethod
    def _parse(payload: Optional[dict], matched_by: str, brand_used: Optional[str]) -> Optional[ContentMatch]:
        data = (payload or {}).get("data") or {}
        urls: List[str] = []

        def add(u):
            if isinstance(u, str) and u.startswith("http") and u not in urls:
                urls.append(u)

        thumbs: dict = {}

        def add_with_thumb(full, entry):
            if isinstance(full, str) and full.startswith("http"):
                add(full)
                small = entry.get("Pic500x500") or entry.get("LowPic") or entry.get("ThumbPic")
                if isinstance(small, str) and small.startswith("http"):
                    thumbs[full] = small

        image = data.get("Image") or {}
        add_with_thumb(image.get("HighPic"), image)
        for pic in data.get("Gallery") or []:
            add_with_thumb(pic.get("Pic"), pic)
        if not urls:
            add_with_thumb(image.get("Pic500x500"), image)
        if not urls:
            return None
        general = data.get("GeneralInfo") or {}
        return ContentMatch(
            images=urls[:MAX_IMAGES],
            title=general.get("Title"),
            icecat_id=str(general.get("IcecatId")) if general.get("IcecatId") else None,
            matched_by=matched_by,
            brand_used=brand_used,
            thumbs={u: thumbs[u] for u in urls[:MAX_IMAGES] if u in thumbs},
        )

    def lookup_with_status(self, brand: Optional[str], mpn: Optional[str], gtin: Optional[str]):
        """
        Returns (match, restricted). match is None for a definitive 'no photo
        available'; restricted is True when at least one lookup was refused
        because the content needs a Full Icecat account (so the miss may be
        resolved by upgrading, unlike a true not-found). Raises
        IcecatContentError when the answer is unknown (retry later).
        """
        restricted = False

        def attempt(params, matched_by, brand_used):
            nonlocal restricted
            try:
                return self._parse(self._get(params), matched_by, brand_used)
            except IcecatRestricted:
                restricted = True
                return None

        digits = re.sub(r"\D", "", gtin or "")
        if len(digits) in (8, 12, 13, 14) and digits.strip("0"):
            match = attempt({"GTIN": digits}, "gtin", None)
            if match:
                return match, False

        code = (mpn or "").strip()
        if code:
            for candidate in brand_candidates(brand):
                match = attempt({"Brand": candidate, "ProductCode": code}, "brand+mpn", candidate)
                if match:
                    return match, False
        return None, restricted

    def lookup(self, brand: Optional[str], mpn: Optional[str], gtin: Optional[str]) -> Optional[ContentMatch]:
        return self.lookup_with_status(brand, mpn, gtin)[0]
