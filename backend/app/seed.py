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

        # 2. Seed Only 2 Real Wholesale Suppliers (Ingram Micro, D&H)
        suppliers_data = [
            {"name": "Ingram Micro", "adapter_class": "IngramMicroAdapter"},
            {"name": "D&H", "adapter_class": "DAndHAdapter"},
        ]

        allowed_supplier_names = [s["name"] for s in suppliers_data]

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

        primary_supplier = created_suppliers[0] if created_suppliers else None

        # Clean up any removed suppliers (TD SYNNEX, Ma Labs, VoiceComm) while preserving products
        old_suppliers = db.query(Supplier).filter(~Supplier.name.in_(allowed_supplier_names)).all()
        for old_s in old_suppliers:
            logger.info(f"Migrating products from removed supplier '{old_s.name}' to '{primary_supplier.name}'...")
            from app.models.supplier_product import SupplierProduct
            # Reassign supplier_products to primary_supplier if not already present
            for sp in list(old_s.supplier_products):
                existing_sp = db.query(SupplierProduct).filter(
                    SupplierProduct.product_id == sp.product_id,
                    SupplierProduct.supplier_id == primary_supplier.id
                ).first()
                if not existing_sp:
                    sp.supplier_id = primary_supplier.id
                else:
                    db.delete(sp)
            db.delete(old_s)
            db.commit()
            logger.info(f"Removed extra supplier: {old_s.name}")

        # 3. Seed Only 3 Real Online Sales Channels (eBay, Amazon, Shopify)
        marketplaces_data = [
            {"name": "eBay", "adapter_class": "LiveEBayAdapter"},
            {"name": "Amazon", "adapter_class": "LiveAmazonAdapter"},
            {"name": "Shopify", "adapter_class": "LiveShopifyAdapter"},
        ]
        allowed_marketplace_names = [m["name"] for m in marketplaces_data]

        # Clean up any extra marketplaces (Walmart, Newegg)
        old_marketplaces = db.query(Marketplace).filter(~Marketplace.name.in_(allowed_marketplace_names)).all()
        for old_m in old_marketplaces:
            db.delete(old_m)
            db.commit()
            logger.info(f"Removed extra marketplace: {old_m.name}")

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

        # 4. Perform catalog sync from Ingram Micro & D&H to ensure all 5 products stay populated
        logger.info("Performing catalog sync from wholesale suppliers (Ingram Micro & D&H)...")
        sync_service = SyncService(db)
        for s in created_suppliers:
            result = sync_service.sync_supplier(s.id)
            logger.info(f"Synced {s.name}: {result['products_imported']} products imported")

        logger.info("Database seeding completed successfully.")

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
