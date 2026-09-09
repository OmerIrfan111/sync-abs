import os
import sys
import json
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.marketplace import Marketplace
from app.core.security import decrypt_credential
from app.adapters.marketplaces.live_amazon import LiveAmazonAdapter

def main():
    db = SessionLocal()
    try:
        amazon = db.query(Marketplace).filter(Marketplace.id == 2).first()
        if not amazon or not amazon.credentials_encrypted:
            print("[ERROR] Amazon credentials not found in database.")
            return

        creds = json.loads(decrypt_credential(amazon.credentials_encrypted))
        adapter = LiveAmazonAdapter(credentials=creds)

        print(f"[*] Initialized LiveAmazonAdapter for Seller ID: {adapter.seller_id}")
        print(f"[*] SP-API Endpoint: {adapter.sp_api_endpoint}")

        print("[*] Calling create_listing() on Amazon...")
        result = adapter.create_listing(
            sku="ING-TEST-001",
            title="Enterprise 4K UltraHD Pro Monitor 32-inch",
            description="Professional 4K UltraHD Monitor with IPS Display",
            price=Decimal("575.00"),
            quantity=10
        )
        print("[SUCCESS] Result from Amazon SP-API:")
        print(json.dumps({k: str(v) for k, v in result.items()}, indent=2))
    finally:
        db.close()

if __name__ == "__main__":
    main()
