#!/usr/bin/env python3
"""
Full D&H funnel probe — Phase 2:
- Confirms working catalog URL (pageSize must be 10-200 and multiple of 10)
- Gets first 100 catalog items, checks all field names
- Runs P&A bulk for first 50 items, checks all P&A field names
- Counts how many items pass/fail the current adapter checks
"""
import os, json, urllib.request, urllib.parse, urllib.error, ssl

CLIENT_ID = os.environ.get('DANDH_CLIENT_ID', '')
CLIENT_SECRET = os.environ.get('DANDH_CLIENT_SECRET', '')
ACCOUNT = os.environ.get('DANDH_ACCOUNT_NUMBER', '3302610000')
TENANT = os.environ.get('DANDH_TENANT', 'dhus')

TOKEN_URL = 'https://auth.dandh.com/api/oauth/token'
BASE_URL = 'https://api.dandh.com/catalog/v1'
OM_URL = 'https://api.dandh.com/customerOrderManagement/v2'
ctx = ssl.create_default_context()

data = urllib.parse.urlencode({
    'grant_type': 'client_credentials',
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'scope': 'resource.READ resource.WRITE',
}).encode()
req = urllib.request.Request(TOKEN_URL, data=data, headers={
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json',
    'User-Agent': 'Probe/1.0',
}, method='POST')
with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
    token_data = json.loads(r.read())
    token = token_data['access_token']
print(f"Token OK (scope={token_data.get('scope')})")

hdrs = {
    'accept': 'application/json',
    'dandh-tenant': TENANT,
    'Authorization': f'Bearer {token}',
    'User-Agent': 'Probe/1.0',
}

print("\n=== STEP 1: pageSize validation ===")
for ps in [10, 20, 50, 100, 200]:
    url = f'{BASE_URL}/customers/{ACCOUNT}/items?countryOfOrigin=US&pageSize={ps}'
    req = urllib.request.Request(url, headers=hdrs, method='GET')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=40) as r:
            d = json.loads(r.read())
            elems = d.get('elements') or []
            print(f"  pageSize={ps}: OK -> {len(elems)} items (hasNext={d.get('hasNext')})")
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        try:
            detail = json.loads(body)
            issues = [f"{det.get('field')}: {det.get('issue')}" for det in (detail.get('details') or [])]
            print(f"  pageSize={ps}: HTTP {e.code} -> {'; '.join(issues)}")
        except Exception:
            print(f"  pageSize={ps}: HTTP {e.code} -> {body[:200]}")
    except Exception as ex:
        print(f"  pageSize={ps}: ERROR {ex}")

print("\n=== STEP 2: Fetch 100 catalog items (pageSize=100) ===")
url = f'{BASE_URL}/customers/{ACCOUNT}/items?countryOfOrigin=US&pageSize=100'
req = urllib.request.Request(url, headers=hdrs, method='GET')
with urllib.request.urlopen(req, context=ctx, timeout=45) as r:
    catalog_resp = json.loads(r.read())

elements = catalog_resp.get('elements') or []
scroll_id = catalog_resp.get('scrollId')
has_next = catalog_resp.get('hasNext')
print(f"  items={len(elements)}  scrollId={'SET' if scroll_id else 'MISSING'}  hasNext={has_next}")

# Gather all keys present across all items
all_keys = set()
for el in elements:
    all_keys.update(el.keys())
print(f"  All catalog item keys: {sorted(all_keys)}")

# Check specific suspect fields
print("\n  Image field presence across 100 items:")
for field in ['imageUrl', 'image', 'thumbnailUrl', 'imageLink', 'productImageUrl', 'links', 'mediaUrl', 'productImage']:
    count = sum(1 for el in elements if el.get(field))
    print(f"    {field:25s}: {count}/100 items have it")

print("\n  Title field presence:")
for field in ['description', 'productName', 'longDescription', 'name', 'title']:
    count_present = sum(1 for el in elements if el.get(field) is not None)
    count_nonempty = sum(1 for el in elements if el.get(field))
    print(f"    {field:25s}: present={count_present}/100  nonempty={count_nonempty}/100")

print("\n  Sample titles (description field):")
for el in elements[:5]:
    print(f"    {el.get('itemId','?'):15s}: {repr(el.get('description','(MISSING)'))[:80]}")

print("\n=== STEP 3: P&A bulk for first 50 items ===")
item_ids = [str(el.get('itemId') or el.get('vendorItemId') or '').strip() for el in elements[:50]]
item_ids = [x for x in item_ids if x]
print(f"  Querying {len(item_ids)} item IDs...")

query_str = urllib.parse.urlencode({'items': ','.join(item_ids)})
pa_url = f'{OM_URL}/customers/{ACCOUNT}/items/priceAndAvailability/bulk?{query_str}'
req = urllib.request.Request(pa_url, headers=hdrs, method='GET')
try:
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        pa_resp = json.loads(r.read())
    print(f"  P&A response type={type(pa_resp).__name__}")

    if isinstance(pa_resp, list):
        print(f"  P&A items returned: {len(pa_resp)} out of {len(item_ids)} queried")
        if pa_resp:
            all_pa_keys = set()
            for pa in pa_resp:
                all_pa_keys.update(pa.keys())
            print(f"  All P&A keys: {sorted(all_pa_keys)}")

            first_pa = pa_resp[0]
            print(f"\n  First P&A item full content:")
            print(json.dumps(first_pa, indent=4, default=str))

            print("\n  Price field check:")
            for field in ['salesPrice', 'unitPrice', 'customerPrice', 'price', 'listPrice', 'netPrice']:
                count = sum(1 for pa in pa_resp if pa.get(field) is not None)
                print(f"    {field:25s}: {count}/{len(pa_resp)} items have it")

            print("\n  Qty field check:")
            for field in ['totalAvailableQuantity', 'availableQuantity', 'totalQty', 'quantity', 'qtyAvailable']:
                count = sum(1 for pa in pa_resp if pa.get(field) is not None)
                print(f"    {field:25s}: {count}/{len(pa_resp)} items have it")

            # Simulate current adapter logic
            print("\n  Current adapter filter simulation (salesPrice + totalAvailableQuantity):")
            would_pass = 0
            would_skip = 0
            skip_reasons = {}
            for pa in pa_resp:
                price = pa.get('salesPrice')
                qty = pa.get('totalAvailableQuantity')
                if price is None or qty is None:
                    would_skip += 1
                    reason = f"salesPrice={'missing' if price is None else 'ok'} totalAvailableQuantity={'missing' if qty is None else 'ok'}"
                    skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                else:
                    would_pass += 1
            print(f"    Would PASS: {would_pass}/{len(pa_resp)}")
            print(f"    Would SKIP: {would_skip}/{len(pa_resp)}")
            for reason, count in skip_reasons.items():
                print(f"      {count}x: {reason}")

    elif isinstance(pa_resp, dict):
        print(f"  P&A is a dict: keys={list(pa_resp.keys())}")
        print(json.dumps(pa_resp, indent=4, default=str)[:1000])
    else:
        print(f"  Unexpected type: {repr(pa_resp)[:200]}")

except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8', errors='replace')
    print(f"  P&A HTTP {e.code}: {body[:400]}")
except Exception as ex:
    print(f"  P&A ERROR: {ex}")

print("\n=== DONE ===")
