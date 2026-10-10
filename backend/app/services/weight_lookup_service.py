import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from app.core.product_matcher import calculate_product_similarity

logger = logging.getLogger(__name__)

# Lower than the image-match threshold (0.6) on purpose: here both titles
# are genuine, well-formed product titles from two *different* catalogs for
# the same real item, and independent vendors word titles very differently
# (our "ADDON HP P00924-B21 COMP 32GB DDR4" vs. UPCitemdb's "AddOn 32GB DDR4
# SDRAM Memory Module" scores ~0.49 despite being the exact same product).
# A genuinely wrong/unrelated match (different product entirely) scores
# near-zero (~0.04 observed), so 0.4 still safely rejects barcode collisions
# while not discarding real matches that are just worded differently.
WEIGHT_MATCH_THRESHOLD = 0.4

_WEIGHT_UNIT_TO_LBS = {
    "lb": 1.0, "lbs": 1.0, "pound": 1.0, "pounds": 1.0,
    "kg": 2.2046226218, "kgs": 2.2046226218, "kilogram": 2.2046226218, "kilograms": 2.2046226218,
    "oz": 0.0625, "ounce": 0.0625, "ounces": 0.0625,
    "g": 0.0022046226, "gram": 0.0022046226, "grams": 0.0022046226,
}


@dataclass
class WeightLookupResult:
    status: str  # "found" or "not_found"
    weight_lbs: Optional[float] = None
    confidence: Optional[float] = None
    source_title: Optional[str] = None
    reason: Optional[str] = None


def _parse_weight_to_lbs(raw: Optional[str]) -> Optional[float]:
    """Parses free-text weight strings ("0.80lb", "1.64 lb", "6.8 kg") into lbs."""
    if not raw or not isinstance(raw, str):
        return None
    match = re.match(r"\s*([\d.]+)\s*([a-zA-Z]+)", raw.strip())
    if not match:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    unit = match.group(2).lower()
    factor = _WEIGHT_UNIT_TO_LBS.get(unit)
    if factor is None or value <= 0:
        return None
    return round(value * factor, 2)


class WeightLookupService:
    """
    Best-effort physical shipping weight lookup by UPC, for suppliers (Ingram
    Micro, TD SYNNEX) that don't report weight at all. Uses UPCitemdb's public
    trial lookup — real third-party barcode aggregator data, not fabricated.

    Deliberately NOT wired into any automated/bulk task: the trial endpoint
    is aggressively rate-limited (observed HTTP 429 after a handful of calls
    with no API key), so this is only safe as an on-demand, staff-triggered
    lookup — never a background sweep across the whole catalog.
    """

    LOOKUP_URL = "https://api.upcitemdb.com/prod/trial/lookup"

    def lookup_weight_by_upc(
        self,
        upc: str,
        title: str,
        brand: Optional[str] = None,
    ) -> WeightLookupResult:
        clean_upc = (upc or "").strip()
        if not clean_upc:
            return WeightLookupResult(status="not_found", reason="No UPC/EAN on file for this product.")

        url = f"{self.LOOKUP_URL}?upc={clean_upc}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                return WeightLookupResult(
                    status="not_found",
                    reason="Weight lookup service is rate-limited right now — try again in a bit.",
                )
            logger.warning(f"Weight lookup HTTP error for UPC {clean_upc}: {exc}")
            return WeightLookupResult(status="not_found", reason=f"Lookup service error: {exc}")
        except Exception as exc:
            logger.warning(f"Weight lookup failed for UPC {clean_upc}: {exc}")
            return WeightLookupResult(status="not_found", reason=f"Lookup failed: {exc}")

        items = data.get("items") or []
        if not items:
            return WeightLookupResult(status="not_found", reason=f"No product found for UPC {clean_upc}.")

        best_item = None
        best_score = 0.0
        for item in items:
            score = calculate_product_similarity(
                title1=title,
                brand1=brand,
                title2=item.get("title") or "",
                brand2=item.get("brand"),
            )
            if score > best_score:
                best_score = score
                best_item = item

        if not best_item or best_score < WEIGHT_MATCH_THRESHOLD:
            return WeightLookupResult(
                status="not_found",
                confidence=best_score,
                source_title=best_item.get("title") if best_item else None,
                reason=(
                    f"Found a product for this UPC, but its title didn't match closely enough "
                    f"(score {best_score:.2f}) to trust its weight — refusing to guess."
                ),
            )

        weight_lbs = _parse_weight_to_lbs(best_item.get("weight"))
        if weight_lbs is None:
            return WeightLookupResult(
                status="not_found",
                confidence=best_score,
                source_title=best_item.get("title"),
                reason="Matched the product but it has no usable weight listed.",
            )

        return WeightLookupResult(
            status="found",
            weight_lbs=weight_lbs,
            confidence=best_score,
            source_title=best_item.get("title"),
        )
