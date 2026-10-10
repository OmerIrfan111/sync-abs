"""
Regression test for a real incident (2026-10-09): the "Set as Permanent
Product Photo" picker showed an actor's photo and a Bollywood movie poster
as suggestions for a $32 HDMI-to-VGA dongle and a USB-C cable. Live-confirmed
root cause: Bing Image Search, for narrow B2B product titles it has little
real indexed content for, returns images with zero topical connection to the
query — not a bot-block or a transient glitch (generic queries like "apple
iphone" returned genuinely relevant results from the same live endpoint at
the same time). There was no relevance check anywhere on this path before
this fix; whatever Bing ranked first was shown directly as a candidate photo.

The exact query/title/purl data below is real output captured live from
Bing on 2026-10-09 for the query "HDMI TO VGA M/F DONGLE C2G" — every single
one of the 12 results it returned was about the actor Irrfan Khan.
"""
from app.adapters.suppliers.image_search_provider import _is_relevant

REAL_QUERY = "HDMI TO VGA M/F DONGLE C2G"

REAL_IRRELEVANT_BING_RESULTS = [
    ("10 Best Films/Movies Made Irrfan Khan a Master of Indian Cinema",
     "https://www.filmingindo.com/blog-post/10-best-movies-made-of-bollywood-actor-irrfan-khan-a-master-of-cinema-died-due-to-cancer/"),
    ("7 best Irrfan Khan movies on Netflix, Amazon Prime Video, Disney+ ...",
     "https://www.gqindia.com/binge-watch/collection/7-best-irrfan-khan-movies-on-netflix-amazon-prime-video-disney-hotstar-youtube-reflect-talent-truest-form/"),
    ("Irfan Khan Movies List",
     "https://ar.inspiredpencil.com/pictures-2023/irfan-khan-movies-list"),
    ("The 12 Best Irrfan Khan Films, Ranked",
     "https://movieweb.com/best-irrfan-khan-films-ranked/"),
]


def test_rejects_the_real_irrelevant_results_that_caused_the_incident():
    for title, purl in REAL_IRRELEVANT_BING_RESULTS:
        assert not _is_relevant(REAL_QUERY, title, purl), f"Should have rejected: {title}"


def test_accepts_a_genuinely_relevant_result():
    assert _is_relevant(
        REAL_QUERY,
        "C2G HDMI to VGA Adapter Converter - 8 inch",
        "https://www.cdw.com/product/c2g-hdmi-to-vga-adapter/1234567",
    )


def test_accepts_result_matching_only_via_purl_not_title():
    # A generic title but a URL that clearly names the real product should
    # still pass — the check looks at both fields, not title alone.
    assert _is_relevant(
        "Belkin USB-C to USB-C Cable",
        "Product Photo",
        "https://www.belkin.com/usb-c-cable/CAB004BT2MBK",
    )


def test_rejects_when_only_generic_stopwords_overlap():
    # Shares only "the"/"best" etc with the query — must not count as a match.
    assert not _is_relevant(
        "HDMI TO VGA M/F DONGLE C2G",
        "The Best New Pack",
        "https://example.com/unrelated",
    )


def test_empty_query_never_filters_anything():
    """No query text to compare against -> nothing to reject (used by callers that don't have one)."""
    assert _is_relevant("", "literally anything", "https://example.com/x")


def test_search_web_images_filters_real_captured_irrelevant_results_end_to_end():
    """
    End-to-end: feeds the exact real Bing HTML shape (regex-matchable
    `class="iusc" ... m="{...}"` blocks) containing the real captured
    irrelevant Irrfan Khan data through search_web_images() itself, proving
    the filter is actually wired into the live code path, not just the
    helper function in isolation.
    """
    import json
    import html as html_mod
    from unittest.mock import patch
    from app.adapters.suppliers.image_search_provider import BingWebImageSearchProvider

    blocks = []
    for title, purl in REAL_IRRELEVANT_BING_RESULTS:
        payload = json.dumps({
            "murl": f"https://example.com/{hash(purl) % 100000}.jpg",
            "t": title,
            "purl": purl,
        })
        blocks.append(f'class="iusc"  m="{html_mod.escape(payload)}"')
    # One genuinely relevant result mixed in, to confirm it survives.
    relevant_payload = json.dumps({
        "murl": "https://cdn.cdwg.com/real-c2g-hdmi-vga-dongle.jpg",
        "t": "C2G HDMI to VGA Adapter - 8 inch",
        "purl": "https://www.cdw.com/product/c2g-hdmi-vga/999",
    })
    blocks.append(f'class="iusc"  m="{html_mod.escape(relevant_payload)}"')
    fake_html = "<html>" + "".join(f"<div {b}></div>" for b in blocks) + "</html>"

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return fake_html.encode("utf-8")

    provider = BingWebImageSearchProvider()
    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        results = provider.search_web_images(REAL_QUERY, max_results=12)

    assert len(results) == 1
    assert "cdwg.com" in results[0].image_url
