#!/usr/bin/env python3
"""Quick variant probe for D&H production catalog API."""
import os, json, urllib.request, urllib.parse, urllib.error, ssl

CLIENT_ID = os.environ.get('DANDH_CLIENT_ID', '')
CLIENT_SECRET = os.environ.get('DANDH_CLIENT_SECRET', '')
ACCOUNT = os.environ.get('DANDH_ACCOUNT_NUMBER', '3302610000')
TENANT = os.environ.get('DANDH_TENANT', 'dhus')

TOKEN_URL = 'https://auth.dandh.com/api/oauth/token'
BASE_URL = 'https://api.dandh.com/catalog/v1'
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
    token = json.loads(r.read())['access_token']
print(f"Token OK")

hdrs = {
    'accept': 'application/json',
    'dandh-tenant': TENANT,
    'Authorization': f'Bearer {token}',
    'User-Agent': 'Probe/1.0',
}

variants = [
    f'{BASE_URL}/customers/{ACCOUNT}/items?countryOfOrigin=US&pageSize=5',
    f'{BASE_URL}/customers/{ACCOUNT}/items?pageSize=5',
    f'{BASE_URL}/customers/{ACCOUNT}/items?limit=5',
    f'{BASE_URL}/customers/{ACCOUNT}/items',
    f'{BASE_URL}/customers/{ACCOUNT}/items?size=5',
    f'{BASE_URL}/customers/{ACCOUNT}/items?page=0&pageSize=5',
    f'{BASE_URL}/customers/{ACCOUNT}/items?countryOfOrigin=US',
]

for url in variants:
    req = urllib.request.Request(url, headers=hdrs, method='GET')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=40) as r:
            d = json.loads(r.read())
            print(f"\nSUCCESS: {url}")
            print(f"  Keys: {list(d.keys())}")
            elems = d.get('elements') or d.get('items') or d.get('data') or []
            print(f"  Items: {len(elems)}")
            if elems:
                print(f"  First item keys: {list(elems[0].keys())}")
                # Show title-candidate fields
                for field in ['description', 'productName', 'longDescription', 'shortDescription', 'name', 'title']:
                    val = elems[0].get(field)
                    print(f"  {field}: {repr(val)[:100]}")
            break
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"\nHTTP {e.code}: {url}")
        try:
            detail = json.loads(body)
            for det in (detail.get('details') or []):
                print(f"  field={det.get('field')} issue={det.get('issue')} value={repr(det.get('value'))}")
        except Exception:
            print(f"  body: {body[:400]}")
    except Exception as ex:
        print(f"\nERR {type(ex).__name__}: {ex}  [{url}]")
