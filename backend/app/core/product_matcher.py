import re
from difflib import SequenceMatcher
from typing import Optional, Tuple, Set
from app.core.config import settings

STOP_WORDS = {
    "the", "a", "an", "and", "or", "for", "with", "in", "on", "at", "by", "from",
    "to", "of", "is", "it", "new", "oem", "genuine", "original", "pack", "pcs"
}

def tokenize(text: Optional[str]) -> Set[str]:
    """Extracts clean alphanumeric tokens, omitting common stop words."""
    if not text:
        return set()
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = set(cleaned.split())
    return {t for t in tokens if t not in STOP_WORDS and len(t) > 1}


def compute_token_similarity(tokens1: Set[str], tokens2: Set[str]) -> float:
    """Computes Jaccard + Overlap coefficient combination."""
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    if not intersection:
        return 0.0
    jaccard = len(intersection) / len(tokens1.union(tokens2))
    overlap = len(intersection) / min(len(tokens1), len(tokens2))
    # Weighted blend favoring containment for titles with extra marketing fluff
    return 0.4 * jaccard + 0.6 * overlap


def compute_string_similarity(str1: str, str2: str) -> float:
    """Computes normalized Levenshtein-like SequenceMatcher ratio."""
    s1 = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", (str1 or "").lower())).strip()
    s2 = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", (str2 or "").lower())).strip()
    if not s1 or not s2:
        return 0.0
    return SequenceMatcher(None, s1, s2).ratio()


def calculate_product_similarity(
    title1: str,
    brand1: Optional[str] = None,
    title2: str = "",
    brand2: Optional[str] = None,
    model1: Optional[str] = None,
    model2: Optional[str] = None,
) -> float:
    """
    Computes a composite similarity score between two product representations.
    Returns a float in [0.0, 1.0].
    Used jointly by Feature 3 (duplicate UPC conflict check) and Feature 4 (image title verification).
    """
    t1_tokens = tokenize(title1)
    t2_tokens = tokenize(title2)

    if not t1_tokens or not t2_tokens:
        return 0.0

    # 1. Token similarity
    token_score = compute_token_similarity(t1_tokens, t2_tokens)

    # 2. Sequence similarity
    seq_score = compute_string_similarity(title1, title2)

    title_score = 0.6 * token_score + 0.4 * seq_score

    # 3. Brand analysis
    b1 = (brand1 or "").strip().lower()
    b2 = (brand2 or "").strip().lower()

    brand_modifier = 1.0

    if b1 and b2:
        if b1 == b2:
            brand_modifier = 1.15
        elif b1 in b2 or b2 in b1:
            brand_modifier = 1.10
        else:
            # Different explicit brands (e.g. Apple vs Samsung or Belkin vs Tripp Lite)
            # If brands conflict and do not appear in each other's titles, penalize
            if b1 not in title2.lower() and b2 not in title1.lower():
                brand_modifier = 0.50
    elif b1:
        if b1 in title2.lower():
            brand_modifier = 1.10
    elif b2:
        if b2 in title1.lower():
            brand_modifier = 1.10

    # 4. Model / MPN analysis
    m1 = (model1 or "").strip().lower()
    m2 = (model2 or "").strip().lower()
    if m1 and m2:
        if m1 == m2:
            brand_modifier *= 1.20
        else:
            brand_modifier *= 0.80

    final_score = min(1.0, title_score * brand_modifier)
    return round(final_score, 4)


def is_same_product(
    title1: str,
    brand1: Optional[str] = None,
    title2: str = "",
    brand2: Optional[str] = None,
    threshold: Optional[float] = None,
) -> Tuple[bool, float]:
    """
    Determines if two products are considered the same product based on the configurable threshold.
    """
    effective_threshold = threshold if threshold is not None else settings.UPC_SIMILARITY_THRESHOLD
    score = calculate_product_similarity(title1, brand1, title2, brand2)
    return (score >= effective_threshold), score
