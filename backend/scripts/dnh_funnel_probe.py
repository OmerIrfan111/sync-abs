#!/usr/bin/env python3
"""
D&H funnel probe: fetches ONE page from the catalog API and ONE P&A batch,
then dumps every field so we can verify:
  1. What the title field is actually called (description vs productName vs longDescription)
  2. What the image field is actually called
  3. What the P&A price field is called (salesPrice vs unitPrice vs customerPrice)
  4. What the P&A quantity field is called (totalAvailableQuantity vs availableQuantity)
  5. Whether branchInventory is returned and what its structure is

Run inside the backend container:
  docker exec sync_backend python scripts/dnh_funnel_probe.py

Output is structured so bugs can be identified at a glance.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import ssl

# ── credentials ──────────────────────────────────────────────────────────────
CLIENT_ID     = os.environ.get("DANDH_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("DANDH_CLIENT_SECRET", "")
ACCOUNT       = os.environ.get("DANDH_ACCOUNT_NUMBER", "3302610000")
TENANT        = os.environ.get("DANDH_TENANT", "dhus")
ENV           = os.environ.get("DANDH_ENVIRONMENT", "production").lower()

if ENV == "production":
    BASE_URL  = "https://api.dandh.com/catalog/v1"
    OM_URL    = "https://api.dandh.com/customerOrderManagement/v2"
    TOKEN_URL = "https://auth.dandh.com/api/oauth/token"
else:
    BASE_URL  = "https://test.api.dandh.com/catalog/v1"
    OM_URL    = "https://test.api.dandh.com/customerOrderManagement/v2"
    TOKEN_URL = "https://test.auth.dandh.com/api/oauth/token"

SCOPE = "resource.READ resource.WRITE"

ctx = ssl.create_default_context()

def get_token():
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPE,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "User-Agent": "SyncABS-DiagnosticProbe/1.0",
    }, method="POST")
    with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
        d = json.loads(r.read())
    print(f"\n[TOKEN] OK — expires_in={d.get('expires_in')}s  scope='{d.get('scope')}'")
    return d["access_token"]

def headers(token):
    return {
        "accept": "application/json",
        "dandh-tenant": TENANT,
        "Authorization": f"Bearer {token}",
        "User-Agent": "SyncABS-DiagnosticProbe/1.0",
    }

def sep(label):
    print("\n" + "═"*70)
    print(f"  {label}")
    print("═"*70)

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 1: Fetch first page of catalog (pageSize=5)
# ─────────────────────────────────────────────────────────────────────────────
token = get_token()

sep("STEP 1 — Catalog API: first 5 items (raw JSON keys)")

# Try variants in order until one works
url_variants = [
    f"{BASE_URL}/customers/{ACCOUNT}/items?countryOfOrigin=US&pageSize=5",
    f"{BASE_URL}/customers/{ACCOUNT}/items?pageSize=5",
]
catalog_resp = None
working_url = None
for url in url_variants:
    print(f"  Trying: {url}")
    req = urllib.request.Request(url, headers=headers(token), method="GET")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=35) as r:
            catalog_resp = json.loads(r.read())
            working_url = url
            print(f"  ✓ SUCCESS")
            break
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  ✗ HTTP {e.code}: {body[:300]}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

if catalog_resp is None:
    print("\n  ALL CATALOG URL VARIANTS FAILED — cannot continue.")
    sys.exit(1)

print(f"\n  Working URL: {working_url}")
elements = catalog_resp.get("elements") or []
print(f"  hasNext     : {catalog_resp.get('hasNext')}")
print(f"  scrollId    : {'SET' if catalog_resp.get('scrollId') else 'MISSING'}")
print(f"  items count : {len(elements)}")

if elements:
    first = elements[0]
    print("\n--- All top-level keys in first catalog item ---")
    for k, v in first.items():
        # Truncate long values for readability
        val_str = str(v)
        if len(val_str) > 120:
            val_str = val_str[:120] + "…"
        print(f"  {k!r:40s}: {val_str}")

    # Highlight specific suspects
    sep("STEP 1b — Suspected field mapping")
    suspects = [
        ("itemId",               "→ used as sku (current code)"),
        ("vendorItemId",         "→ used as sku fallback + mpn (current code)"),
        ("description",          "→ used as title (SUSPECT: may be wrong or empty)"),
        ("productName",          "→ POSSIBLE REAL TITLE FIELD (not used by current code)"),
        ("longDescription",      "→ POSSIBLE REAL TITLE FIELD (not used by current code)"),
        ("shortDescription",     "→ POSSIBLE REAL TITLE FIELD (not used by current code)"),
        ("name",                 "→ POSSIBLE REAL TITLE FIELD (not used by current code)"),
        ("vendorName",           "→ used as brand (current code)"),
        ("universalProductCode", "→ used as upc (current code)"),
        ("category",             "→ used as category (current code)"),
        ("subcategory",          "→ used as sub_category (current code)"),
        ("imageUrl",             "→ tried first for image (current code)"),
        ("image",                "→ tried second for image (current code)"),
        ("thumbnailUrl",         "→ tried third for image (current code)"),
        ("imageLink",            "→ tried fourth for image (current code)"),
        ("productImageUrl",      "→ tried fifth for image (current code)"),
        ("links",                "→ checked for rel=image (current code)"),
        ("itemStatus",           "→ used for availability_status (current code)"),
        ("itemType",             "→ stored in specs (current code)"),
        ("shippingDimensions",   "→ used for weight (current code)"),
    ]
    for field, note in suspects:
        val = first.get(field)
        marker = "✓" if val is not None else "✗ MISSING"
        val_str = repr(val)[:90] if val is not None else "(not present)"
        print(f"  [{marker}] {field!r:30s} {note}")
        if val is not None:
            print(f"            value = {val_str}")

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 2: Fetch P&A for the same items
# ─────────────────────────────────────────────────────────────────────────────
item_ids = []
for el in elements:
    sku = str(el.get("itemId") or el.get("vendorItemId") or "").strip()
    if sku:
        item_ids.append(sku)

sep(f"STEP 2 — P&A bulk query for {len(item_ids)} items")
query_str = urllib.parse.urlencode({"items": ",".join(item_ids)})
pa_url = f"{OM_URL}/customers/{ACCOUNT}/items/priceAndAvailability/bulk?{query_str}"
req = urllib.request.Request(pa_url, headers=headers(token), method="GET")
with urllib.request.urlopen(req, context=ctx, timeout=25) as r:
    pa_resp = json.loads(r.read())

print(f"  P&A response type : {type(pa_resp).__name__}")
if isinstance(pa_resp, list):
    print(f"  P&A items returned: {len(pa_resp)}")
    if pa_resp:
        first_pa = pa_resp[0]
        print("\n--- All top-level keys in first P&A item ---")
        for k, v in first_pa.items():
            val_str = str(v)
            if len(val_str) > 120:
                val_str = val_str[:120] + "…"
            print(f"  {k!r:40s}: {val_str}")

        sep("STEP 2b — Suspected P&A field mapping")
        pa_suspects = [
            ("itemId",                 "→ used as key (current code)"),
            ("salesPrice",             "→ used as cost (SUSPECT: may be wrong name)"),
            ("unitPrice",              "→ POSSIBLE REAL PRICE FIELD"),
            ("customerPrice",          "→ POSSIBLE REAL PRICE FIELD"),
            ("price",                  "→ POSSIBLE REAL PRICE FIELD"),
            ("totalAvailableQuantity", "→ used as qty (SUSPECT: may be wrong name)"),
            ("availableQuantity",      "→ POSSIBLE REAL QTY FIELD"),
            ("totalQty",               "→ POSSIBLE REAL QTY FIELD"),
            ("quantity",               "→ POSSIBLE REAL QTY FIELD"),
            ("branchInventory",        "→ used for per-warehouse stock (current code)"),
        ]
        for field, note in pa_suspects:
            val = first_pa.get(field)
            marker = "✓" if val is not None else "✗ MISSING"
            val_str = repr(val)[:90] if val is not None else "(not present)"
            print(f"  [{marker}] {field!r:30s} {note}")
            if val is not None:
                print(f"            value = {val_str}")

        # Show branchInventory structure if present
        bi = first_pa.get("branchInventory")
        if bi:
            sep("STEP 2c — branchInventory structure")
            for branch in (bi if isinstance(bi, list) else [bi])[:3]:
                print(json.dumps(branch, indent=4))
        else:
            print("\n  ⚠  branchInventory is NOT present in P&A response")

elif isinstance(pa_resp, dict):
    print("  P&A returned a dict (unexpected — check structure):")
    for k, v in pa_resp.items():
        print(f"  {k!r}: {str(v)[:120]}")
else:
    print(f"  P&A returned: {repr(pa_resp)[:200]}")

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 3: Cross-match — how many catalog items have a P&A result?
# ─────────────────────────────────────────────────────────────────────────────
sep("STEP 3 — Cross-match: which catalog items have P&A data?")
if isinstance(pa_resp, list):
    pa_by_id = {str(e.get("itemId","")).strip(): e for e in pa_resp}
else:
    pa_by_id = {}

for el in elements:
    sku = str(el.get("itemId") or el.get("vendorItemId") or "").strip()
    pa = pa_by_id.get(sku)
    has_price = pa is not None and (
        pa.get("salesPrice") is not None or pa.get("unitPrice") is not None
        or pa.get("customerPrice") is not None or pa.get("price") is not None
    )
    has_qty = pa is not None and (
        pa.get("totalAvailableQuantity") is not None
        or pa.get("availableQuantity") is not None
        or pa.get("totalQty") is not None
        or pa.get("quantity") is not None
    )
    desc = el.get("description") or el.get("productName") or el.get("name") or "(NO TITLE)"
    print(f"  SKU {sku:12s}: P&A={'YES' if pa else 'NO ':3s}  price={'YES' if has_price else 'NO ':3s}  qty={'YES' if has_qty else 'NO ':3s}  title={desc!r:.60s}")

sep("DONE — Review output above to identify field-name mismatches")
print()
