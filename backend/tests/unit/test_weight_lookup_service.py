import json
from unittest.mock import patch, MagicMock

from app.services.weight_lookup_service import WeightLookupService, _parse_weight_to_lbs


def _mock_response(payload: dict):
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(payload).encode("utf-8")
    return cm


def test_parse_weight_to_lbs_units():
    assert _parse_weight_to_lbs("0.80lb") == 0.8
    assert _parse_weight_to_lbs("1.64 lb") == 1.64
    assert round(_parse_weight_to_lbs("1 kg"), 2) == 2.20
    assert _parse_weight_to_lbs("16 oz") == 1.0
    assert _parse_weight_to_lbs(None) is None
    assert _parse_weight_to_lbs("unknown") is None


def test_weight_lookup_accepts_verified_match():
    payload = {
        "code": "OK",
        "items": [{"title": "AddOn 32GB DDR4 SDRAM Memory Module", "brand": "AddOn", "weight": "0.80lb"}],
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
        result = WeightLookupService().lookup_weight_by_upc(
            upc="0821456211808", title="ADDON HP P00924-B21 COMP 32GB DDR4", brand="Addon"
        )
    assert result.status == "found"
    assert result.weight_lbs == 0.8


def test_weight_lookup_rejects_mismatched_title():
    payload = {
        "code": "OK",
        "items": [{"title": "Stabilo Point 88 Fineliner Marker Pen", "brand": "STABILO", "weight": "6.8 kg"}],
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
        result = WeightLookupService().lookup_weight_by_upc(
            upc="4006381333931", title="ADDON HP P00924-B21 COMP 32GB DDR4", brand="Addon"
        )
    assert result.status == "not_found"
    assert result.weight_lbs is None


def test_weight_lookup_no_upc():
    result = WeightLookupService().lookup_weight_by_upc(upc="", title="Something", brand=None)
    assert result.status == "not_found"


def test_weight_lookup_no_items_found():
    payload = {"code": "OK", "items": []}
    with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
        result = WeightLookupService().lookup_weight_by_upc(upc="0000000000000", title="X", brand=None)
    assert result.status == "not_found"
