#!/usr/bin/env python3
"""
Compare D&H test vs production in-stock ratios for the first 50 items.
"""
import os, json, urllib.request, urllib.parse, urllib.error, ssl

ctx = ssl.create_default_context()

configs = {
    "TEST (old DB creds)": {
        "client_id": "16cafc81-989d-426a-9774-4f41ee23a53a",
        "client_secret": "b2aef330-e9a1-4013-9533-bd78f6606b4c",
        "token_url": "https://test.auth.dandh.com/api/oauth/token",
        "base_url": "https://test.api.dandh.com/catalog/v1",
        "om_url": "https://test.api.dandh.com/customerOrderManagement/v2",
    },
    "PRODUCTION (.env creds)": {
        "client_id": os.environ.get("DANDH_CLIENT_ID", ""),
        "client_secret": os.environ.get("DANDH_CLIENT_SECRET", ""),
        "token_url": "https://auth.dandh.com/api/oauth/token",
        "base_url": "https://api.dandh.com/catalog/v1",
        "om_url": "https://api.dandh.com/customerOrderManagement/v2",
    },
}

ACCOUNT = os.environ.get("DANDH_ACCOUNT_NUMBER", "3302610000")
TENANT = os.environ.get("DANDH_TENANT", "dhus")

for label, cfg in configs.items():
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    try:
        data = urllib.parse.urlencode({
            'grant_type': 'client_credentials',
            'client_id': cfg['client_id'],
            'client_secret': cfg['client_secret'],
            'scope': 'resource.READ resource.WRITE',
        }).encode()
        req = urllib.request.Request(cfg['token_url'], data=data, headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        }, method='POST')
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            token_data = json.loads(r.read())
        token = token_data['access_token']
        print(f"  Token: OK (scope={token_data.get('scope')})")
    except Exception as ex:
        print(f"  Token FAILED: {ex}")
        continue

    hdrs = {
        'accept': 'application/json',
        'dandh-tenant': TENANT,
        'Authorization': f'Bearer {token}',
        'User-Agent': 'Probe/1.0',
    }

    # Get 50 catalog items
    url = f"{cfg['base_url']}/customers/{ACCOUNT}/items?countryOfOrigin=US&pageSize=50"
    req = urllib.request.Request(url, headers=hdrs, method='GET')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=40) as r:
            cat = json.loads(r.read())
        elements = cat.get('elements') or []
        print(f"  Catalog: {len(elements)} items (hasNext={cat.get('hasNext')})")
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"  Catalog HTTP {e.code}: {body[:300]}")
        continue

    item_ids = [str(el.get('itemId') or '').strip() for el in elements if el.get('itemId')]
    print(f"  Item IDs: {len(item_ids)}")

    # P&A
    query_str = urllib.parse.urlencode({'items': ','.join(item_ids[:50])})
    pa_url = f"{cfg['om_url']}/customers/{ACCOUNT}/items/priceAndAvailability/bulk?{query_str}"
    req = urllib.request.Request(pa_url, headers=hdrs, method='GET')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            pa_resp = json.loads(r.read())
        if isinstance(pa_resp, list):
            in_stock = sum(1 for pa in pa_resp if (pa.get('totalAvailableQuantity') or 0) > 0)
            zero_stock = sum(1 for pa in pa_resp if (pa.get('totalAvailableQuantity') or 0) == 0)
            total_qty = sum((pa.get('totalAvailableQuantity') or 0) for pa in pa_resp)
            print(f"  P&A returned: {len(pa_resp)} items")
            print(f"  In-stock (qty>0): {in_stock}")
            print(f"  Zero-stock:       {zero_stock}")
            print(f"  Total quantity:   {total_qty}")
            if pa_resp:
                sample = [(pa['itemId'], pa.get('totalAvailableQuantity'), pa.get('salesPrice')) for pa in pa_resp[:5]]
                print(f"  Sample: {sample}")
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"  P&A HTTP {e.code}: {body[:300]}")
    except Exception as ex:
        print(f"  P&A ERROR: {ex}")

print("\n=== DONE ===")
