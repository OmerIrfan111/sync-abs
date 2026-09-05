from typing import List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from app.models.product import Product
from app.models.supplier_product import SupplierProduct
from app.models.supplier import Supplier
from app.models.sync_log import SyncLog
from app.schemas.supplier import NormalizedProduct
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, SupplierProductInfo

class CatalogService:
    def __init__(self, db: Session):
        self.db = db

    def find_matching_product(self, item: NormalizedProduct) -> Optional[Product]:
        """
        Product Matching Engine (Spec Section 12):
        Matches incoming items by UPC, EAN, MPN, or SKU against existing products.
        """
        match_conditions = []
        if item.upc:
            match_conditions.append(Product.upc == item.upc)
        if item.ean:
            match_conditions.append(Product.ean == item.ean)
        if item.mpn:
            match_conditions.append(Product.mpn == item.mpn)
        if item.supplier_sku:
            match_conditions.append(Product.sku == item.supplier_sku)

        if not match_conditions:
            return None

        return self.db.query(Product).filter(or_(*match_conditions)).first()

    def upsert_supplier_product(self, supplier: Supplier, item: NormalizedProduct) -> Tuple[Product, SupplierProduct, List[SyncLog]]:
        """
        Normalizes and links supplier products to central catalog, performing change detection (Spec Section 19).
        """
        logs: List[SyncLog] = []
        product = self.find_matching_product(item)

        # 1. If product doesn't exist yet, create canonical product
        if not product:
            product = Product(
                sku=item.supplier_sku,
                upc=item.upc,
                ean=item.ean,
                mpn=item.mpn,
                title=item.title,
                brand=item.brand,
                description=item.description,
                category=item.category,
                images=item.images,
                specs_json=item.specs,
                is_enabled=True
            )
            self.db.add(product)
            self.db.flush()
            logs.append(SyncLog(
                product_id=product.id,
                supplier_id=supplier.id,
                field_changed="product_created",
                old_value=None,
                new_value=product.sku
            ))

        # 2. Check existing supplier product link
        supplier_prod = self.db.query(SupplierProduct).filter(
            SupplierProduct.product_id == product.id,
            SupplierProduct.supplier_id == supplier.id
        ).first()

        now = datetime.now(timezone.utc)

        if not supplier_prod:
            supplier_prod = SupplierProduct(
                product_id=product.id,
                supplier_id=supplier.id,
                supplier_sku=item.supplier_sku,
                cost=item.cost,
                qty_available=item.quantity,
                stock_status=item.stock_status,
                availability_status=item.availability_status,
                shipping_info=item.shipping_info,
                last_seen_at=now
            )
            self.db.add(supplier_prod)
            logs.append(SyncLog(
                product_id=product.id,
                supplier_id=supplier.id,
                field_changed="supplier_linked",
                old_value=None,
                new_value=f"Cost: {item.cost}, Qty: {item.quantity}"
            ))
        else:
            # Change detection (Spec Section 19)
            if supplier_prod.cost != item.cost:
                logs.append(SyncLog(
                    product_id=product.id,
                    supplier_id=supplier.id,
                    field_changed="cost",
                    old_value=str(supplier_prod.cost),
                    new_value=str(item.cost)
                ))
                supplier_prod.cost = item.cost

            if supplier_prod.qty_available != item.quantity:
                logs.append(SyncLog(
                    product_id=product.id,
                    supplier_id=supplier.id,
                    field_changed="qty_available",
                    old_value=str(supplier_prod.qty_available),
                    new_value=str(item.quantity)
                ))
                supplier_prod.qty_available = item.quantity

            if supplier_prod.stock_status != item.stock_status:
                logs.append(SyncLog(
                    product_id=product.id,
                    supplier_id=supplier.id,
                    field_changed="stock_status",
                    old_value=supplier_prod.stock_status,
                    new_value=item.stock_status
                ))
                supplier_prod.stock_status = item.stock_status

            supplier_prod.last_seen_at = now
            supplier_prod.shipping_info = item.shipping_info
            supplier_prod.availability_status = item.availability_status

        for log in logs:
            self.db.add(log)

        self.db.commit()
        self.db.refresh(product)
        self.db.refresh(supplier_prod)
        return product, supplier_prod, logs

    def get_products(
        self,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        supplier_id: Optional[int] = None,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        in_stock: Optional[bool] = None
    ) -> Tuple[List[ProductResponse], int]:
        query = self.db.query(Product)

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Product.sku.ilike(pattern),
                    Product.upc.ilike(pattern),
                    Product.ean.ilike(pattern),
                    Product.mpn.ilike(pattern),
                    Product.title.ilike(pattern),
                    Product.brand.ilike(pattern)
                )
            )

        if brand:
            query = query.filter(Product.brand == brand)
        if category:
            query = query.filter(Product.category == category)

        if supplier_id:
            query = query.join(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id)

        if in_stock is True:
            in_stock_subquery = self.db.query(SupplierProduct.product_id).filter(SupplierProduct.qty_available > 0).distinct().subquery()
            query = query.filter(Product.id.in_(in_stock_subquery))
        elif in_stock is False:
            in_stock_subquery = self.db.query(SupplierProduct.product_id).filter(SupplierProduct.qty_available > 0).distinct().subquery()
            query = query.filter(~Product.id.in_(in_stock_subquery))

        total = query.count()
        products = query.order_by(desc(Product.updated_at)).offset(skip).limit(limit).all()

        results = []
        for p in products:
            sp_infos = []
            total_stock = 0
            costs = []
            for sp in p.supplier_products:
                sp_infos.append(SupplierProductInfo(
                    id=sp.id,
                    supplier_id=sp.supplier_id,
                    supplier_name=sp.supplier.name if sp.supplier else None,
                    supplier_sku=sp.supplier_sku,
                    cost=sp.cost,
                    qty_available=sp.qty_available,
                    stock_status=sp.stock_status,
                    availability_status=sp.availability_status,
                    shipping_info=sp.shipping_info or {},
                    last_seen_at=sp.last_seen_at
                ))
                total_stock += sp.qty_available
                costs.append(sp.cost)

            results.append(ProductResponse(
                id=p.id,
                sku=p.sku,
                upc=p.upc,
                ean=p.ean,
                mpn=p.mpn,
                title=p.title,
                brand=p.brand,
                description=p.description,
                category=p.category,
                images=p.images or [],
                specs_json=p.specs_json or {},
                is_enabled=p.is_enabled,
                created_at=p.created_at,
                updated_at=p.updated_at,
                supplier_products=sp_infos,
                total_stock=total_stock,
                lowest_cost=min(costs) if costs else None
            ))

        return results, total

    def get_product_by_id(self, product_id: int) -> Optional[ProductResponse]:
        p = self.db.query(Product).filter(Product.id == product_id).first()
        if not p:
            return None

        sp_infos = []
        total_stock = 0
        costs = []
        for sp in p.supplier_products:
            sp_infos.append(SupplierProductInfo(
                id=sp.id,
                supplier_id=sp.supplier_id,
                supplier_name=sp.supplier.name if sp.supplier else None,
                supplier_sku=sp.supplier_sku,
                cost=sp.cost,
                qty_available=sp.qty_available,
                stock_status=sp.stock_status,
                availability_status=sp.availability_status,
                shipping_info=sp.shipping_info or {},
                last_seen_at=sp.last_seen_at
            ))
            total_stock += sp.qty_available
            costs.append(sp.cost)

        return ProductResponse(
            id=p.id,
            sku=p.sku,
            upc=p.upc,
            ean=p.ean,
            mpn=p.mpn,
            title=p.title,
            brand=p.brand,
            description=p.description,
            category=p.category,
            images=p.images or [],
            specs_json=p.specs_json or {},
            is_enabled=p.is_enabled,
            created_at=p.created_at,
            updated_at=p.updated_at,
            supplier_products=sp_infos,
            total_stock=total_stock,
            lowest_cost=min(costs) if costs else None
        )
