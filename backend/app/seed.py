import logging
from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.user import User
from app.models.supplier import Supplier
from app.models.marketplace import Marketplace
from app.services.sync_service import SyncService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Seed Admin User
        admin_email = "admin@syncplatform.io"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                email=admin_email,
                hashed_password=get_password_hash("adminpassword123"),
                full_name="Platform Administrator",
                is_active=True,
                is_superuser=True
            )
            db.add(admin)
            db.commit()
            logger.info(f"Admin user seeded: {admin_email}")

        # 2. Seed 5 Suppliers (Spec Section 3)
        suppliers_data = [
            {"name": "Ingram Micro", "adapter_class": "IngramMicroAdapter"},
            {"name": "D&H", "adapter_class": "DAndHAdapter"},
            {"name": "TD SYNNEX", "adapter_class": "TDSynnexAdapter"},
            {"name": "Ma Labs", "adapter_class": "MaLabsAdapter"},
            {"name": "VoiceComm", "adapter_class": "VoiceCommAdapter"},
        ]

        created_suppliers = []
        for s_data in suppliers_data:
            s = db.query(Supplier).filter(Supplier.name == s_data["name"]).first()
            if not s:
                s = Supplier(
                    name=s_data["name"],
                    adapter_class=s_data["adapter_class"],
                    is_active=True
                )
                db.add(s)
                db.commit()
                db.refresh(s)
                logger.info(f"Supplier registered: {s.name}")
            else:
                s.adapter_class = s_data["adapter_class"]
                db.commit()
            created_suppliers.append(s)

        # 3. Seed 5 Marketplaces (Spec Section 3)
        marketplaces_data = [
            {"name": "eBay", "adapter_class": "MockEBayAdapter"},
            {"name": "Amazon", "adapter_class": "MockAmazonAdapter"},
            {"name": "Walmart", "adapter_class": "MockWalmartAdapter"},
            {"name": "Shopify", "adapter_class": "MockShopifyAdapter"},
            {"name": "Newegg", "adapter_class": "MockNeweggAdapter"},
        ]

        for m_data in marketplaces_data:
            m = db.query(Marketplace).filter(Marketplace.name == m_data["name"]).first()
            if not m:
                m = Marketplace(
                    name=m_data["name"],
                    adapter_class=m_data["adapter_class"],
                    is_active=True
                )
                db.add(m)
                db.commit()
                logger.info(f"Marketplace registered: {m.name}")
            else:
                m.adapter_class = m_data["adapter_class"]
                db.commit()

        # 4. Perform initial supplier sync to populate central catalog
        logger.info("Performing initial catalog sync from mock suppliers...")
        sync_service = SyncService(db)
        for s in created_suppliers:
            result = sync_service.sync_supplier(s.id)
            logger.info(f"Synced {s.name}: {result['products_imported']} products imported")

        logger.info("Database seeding completed successfully.")

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
