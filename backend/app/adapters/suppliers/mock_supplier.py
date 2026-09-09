import time
import random
from decimal import Decimal
from typing import List, Dict, Any, Optional
from app.adapters.suppliers.base import SupplierAdapter
from app.schemas.supplier import NormalizedProduct

# In-memory dynamic mock storage to allow programmatic simulation of price/stock changes across test runs
MOCK_SUPPLIER_STATE: Dict[str, Dict[str, Dict[str, Any]]] = {}

DEFAULT_SEED_DATA = {
    "Ingram Micro": [
        {
            "supplier_sku": "ING-LOGI-MXKEYS",
            "upc": "097855149367",
            "ean": "5099206085800",
            "mpn": "920-009400",
            "title": "Logitech MX Keys Advanced Wireless Illuminated Keyboard",
            "brand": "Logitech",
            "description": "Master series keyboard crafted for creatives and engineered for coders.",
            "category": "Computer Accessories",
            "images": ["https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=500&auto=format&fit=crop"],
            "specs": {"connectivity": "Bluetooth/USB Receiver", "color": "Space Gray", "backlight": "Yes"},
            "cost": Decimal("50.00"),
            "quantity": 20,
            "stock_status": "IN_STOCK",
            "shipping_info": {"weight_lbs": 2.2, "lead_time_days": 2},
            "availability_status": "ACTIVE"
        },
        {
            "supplier_sku": "ING-TEST-001",
            "upc": "840080500111",
            "ean": "0840080500111",
            "mpn": "TEST-001",
            "title": "Enterprise 4K UltraHD Pro Monitor 32-inch",
            "brand": "TechPro",
            "description": "Professional color-accurate IPS display with Thunderbolt 4 docking.",
            "category": "Monitors",
            "images": ["https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&auto=format&fit=crop"],
            "specs": {"resolution": "3840x2160", "refresh_rate": "144Hz", "panel": "IPS"},
            "cost": Decimal("500.00"),
            "quantity": 20,
            "stock_status": "IN_STOCK",
            "shipping_info": {"weight_lbs": 16.5, "lead_time_days": 1},
            "availability_status": "ACTIVE"
        },
        {
            "supplier_sku": "ING-SAMS-T7-1TB",
            "upc": "887276435342",
            "ean": "0887276435342",
            "mpn": "MU-PC1T0T/AM",
            "title": "Samsung T7 Portable SSD 1TB USB 3.2 Gen 2",
            "brand": "Samsung",
            "description": "Lightning fast external storage transferring files at up to 1050MB/s.",
            "category": "Storage",
            "images": ["https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=500&auto=format&fit=crop"],
            "specs": {"capacity": "1TB", "interface": "USB 3.2 Gen 2", "color": "Titan Gray"},
            "cost": Decimal("91.00"),
            "quantity": 40,
            "stock_status": "IN_STOCK",
            "shipping_info": {"weight_lbs": 0.5, "lead_time_days": 2},
            "availability_status": "ACTIVE"
        },
        {
            "supplier_sku": "ING-COR-DDR5-32G",
            "upc": "840006659914",
            "ean": "0840006659914",
            "mpn": "CMK32GX5M2B5600C36",
            "title": "Corsair Vengeance 32GB (2x16GB) DDR5 5600MHz RAM",
            "brand": "Corsair",
            "description": "High performance DDR5 desktop memory with onboard power management.",
            "category": "Components",
            "images": ["https://images.unsplash.com/photo-1541029071515-84cc54f84dc5?w=500&auto=format&fit=crop"],
            "specs": {"capacity": "32GB", "speed": "5600MHz", "type": "DDR5"},
            "cost": Decimal("95.00"),
            "quantity": 30,
            "stock_status": "IN_STOCK",
            "shipping_info": {"weight_lbs": 0.4, "lead_time_days": 2},
            "availability_status": "ACTIVE"
        },
        {
            "supplier_sku": "ING-ANKER-65W-CHG",
            "upc": "194644022884",
            "ean": "0194644022884",
            "mpn": "A2663111",
            "title": "Anker Nano II 65W GaN Fast Wall Charger",
            "brand": "Anker",
            "description": "Ultra-compact fast USB-C charger for phone, tablet, and notebook.",
            "category": "Mobile Accessories",
            "images": ["https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=500&auto=format&fit=crop"],
            "specs": {"wattage": "65W", "technology": "GaN II", "ports": "1 USB-C"},
            "cost": Decimal("24.00"),
            "quantity": 120,
            "stock_status": "IN_STOCK",
            "shipping_info": {"weight_lbs": 0.3, "lead_time_days": 1},
            "availability_status": "ACTIVE"
        }
    ],
    "D&H": [
        {
            "supplier_sku": "DH-LOGI-MXKEYS",
            "upc": "097855149367",
            "ean": "5099206085800",
            "mpn": "920-009400",
            "title": "Logitech MX Keys Wireless Keyboard (Graphite)",
            "brand": "Logitech",
            "description": "Comfortable typing keys with smart illumination and USB-C recharging.",
            "category": "Computer Accessories",
            "images": ["https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=500&auto=format&fit=crop"],
            "specs": {"connectivity": "Bluetooth/USB Receiver", "color": "Graphite", "backlight": "Yes"},
            "cost": Decimal("52.00"),
            "quantity": 50,
            "stock_status": "IN_STOCK",
            "shipping_info": {"weight_lbs": 2.3, "lead_time_days": 3},
            "availability_status": "ACTIVE"
        },
        {
            "supplier_sku": "DH-TEST-001",
            "upc": "840080500111",
            "ean": "0840080500111",
            "mpn": "TEST-001",
            "title": "Enterprise 4K UltraHD Pro Monitor 32-inch",
            "brand": "TechPro",
            "description": "Professional color-accurate IPS display with Thunderbolt 4 docking.",
            "category": "Monitors",
            "images": ["https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&auto=format&fit=crop"],
            "specs": {"resolution": "3840x2160", "refresh_rate": "144Hz", "panel": "IPS"},
            "cost": Decimal("510.00"),
            "quantity": 15,
            "stock_status": "IN_STOCK",
            "shipping_info": {"weight_lbs": 16.5, "lead_time_days": 2},
            "availability_status": "ACTIVE"
        },
        {
            "supplier_sku": "DH-SAMS-T7-1TB",
            "upc": "887276435342",
            "ean": "0887276435342",
            "mpn": "MU-PC1T0T/AM",
            "title": "Samsung T7 Portable SSD 1TB USB 3.2 Gen 2",
            "brand": "Samsung",
            "description": "Lightning fast external storage transferring files at up to 1050MB/s.",
            "category": "Storage",
            "images": ["https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=500&auto=format&fit=crop"],
            "specs": {"capacity": "1TB", "interface": "USB 3.2 Gen 2", "color": "Titan Gray"},
            "cost": Decimal("89.00"),
            "quantity": 75,
            "stock_status": "IN_STOCK",
            "shipping_info": {"weight_lbs": 0.5, "lead_time_days": 1},
            "availability_status": "ACTIVE"
        },
        {
            "supplier_sku": "DH-COR-DDR5-32G",
            "upc": "840006659914",
            "ean": "0840006659914",
            "mpn": "CMK32GX5M2B5600C36",
            "title": "Corsair Vengeance 32GB (2x16GB) DDR5 5600MHz RAM",
            "brand": "Corsair",
            "description": "High performance DDR5 desktop memory with onboard power management.",
            "category": "Components",
            "images": ["https://images.unsplash.com/photo-1541029071515-84cc54f84dc5?w=500&auto=format&fit=crop"],
            "specs": {"capacity": "32GB", "speed": "5600MHz", "type": "DDR5"},
            "cost": Decimal("97.00"),
            "quantity": 25,
            "stock_status": "IN_STOCK",
            "shipping_info": {"weight_lbs": 0.4, "lead_time_days": 2},
            "availability_status": "ACTIVE"
        },
        {
            "supplier_sku": "DH-ANKER-65W-CHG",
            "upc": "194644022884",
            "ean": "0194644022884",
            "mpn": "A2663111",
            "title": "Anker Nano II 65W GaN Fast Wall Charger",
            "brand": "Anker",
            "description": "Ultra-compact fast USB-C charger for phone, tablet, and notebook.",
            "category": "Mobile Accessories",
            "images": ["https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=500&auto=format&fit=crop"],
            "specs": {"wattage": "65W", "technology": "GaN II", "ports": "1 USB-C"},
            "cost": Decimal("25.00"),
            "quantity": 80,
            "stock_status": "IN_STOCK",
            "shipping_info": {"weight_lbs": 0.3, "lead_time_days": 1},
            "availability_status": "ACTIVE"
        }
    ]
}

class MockSupplierAdapter(SupplierAdapter):
    """
    Mock adapter fulfilling Section 8 & Section 28 requirements.
    Simulates high-fidelity catalog data, stock changes, cost swings,
    OOS events, latency, and controlled failures.
    """

    def __init__(self, supplier_name: str = "Ingram Micro", credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(credentials=credentials, config=config)
        self.supplier_name = supplier_name
        self._ensure_initialized()

    def _ensure_initialized(self):
        if self.supplier_name not in MOCK_SUPPLIER_STATE:
            MOCK_SUPPLIER_STATE[self.supplier_name] = {}
            items = DEFAULT_SEED_DATA.get(self.supplier_name, DEFAULT_SEED_DATA.get("Ingram Micro", []))
            for item in items:
                sku = item["supplier_sku"]
                MOCK_SUPPLIER_STATE[self.supplier_name][sku] = dict(item)

    def test_connection(self) -> bool:
        if self.config.get("simulate_auth_failure"):
            raise PermissionError("Simulated 401 Unauthorized: Invalid supplier API key")
        if self.config.get("simulate_connection_failure"):
            raise ConnectionError("Simulated 503 Service Unavailable: Supplier gateway timeout")
        return True

    def fetch_catalog(self) -> List[NormalizedProduct]:
        self.test_connection()
        if self.config.get("simulate_latency_ms"):
            time.sleep(self.config["simulate_latency_ms"] / 1000.0)

        products = []
        supplier_data = MOCK_SUPPLIER_STATE.get(self.supplier_name, {})
        for _, raw in supplier_data.items():
            products.append(NormalizedProduct(
                supplier_sku=raw["supplier_sku"],
                upc=raw.get("upc"),
                ean=raw.get("ean"),
                mpn=raw.get("mpn"),
                title=raw["title"],
                brand=raw.get("brand"),
                description=raw.get("description"),
                category=raw.get("category"),
                images=raw.get("images", []),
                specs=raw.get("specs", {}),
                cost=raw["cost"],
                quantity=raw["quantity"],
                stock_status="OUT_OF_STOCK" if raw["quantity"] <= 0 else raw.get("stock_status", "IN_STOCK"),
                shipping_info=raw.get("shipping_info", {}),
                availability_status=raw.get("availability_status", "ACTIVE")
            ))
        return products

    def fetch_inventory(self, skus: Optional[List[str]] = None) -> Dict[str, int]:
        self.test_connection()
        supplier_data = MOCK_SUPPLIER_STATE.get(self.supplier_name, {})
        result = {}
        target_skus = skus if skus is not None else list(supplier_data.keys())
        for sku in target_skus:
            if sku in supplier_data:
                result[sku] = supplier_data[sku]["quantity"]
        return result

    def fetch_price_changes(self) -> Dict[str, Decimal]:
        self.test_connection()
        supplier_data = MOCK_SUPPLIER_STATE.get(self.supplier_name, {})
        return {sku: data["cost"] for sku, data in supplier_data.items()}

    # Utility method for automated tests to simulate dynamic state changes
    @classmethod
    def set_mock_product(cls, supplier_name: str, supplier_sku: str, cost: Optional[Decimal] = None, quantity: Optional[int] = None):
        if supplier_name in MOCK_SUPPLIER_STATE and supplier_sku in MOCK_SUPPLIER_STATE[supplier_name]:
            if cost is not None:
                MOCK_SUPPLIER_STATE[supplier_name][supplier_sku]["cost"] = Decimal(str(cost))
            if quantity is not None:
                MOCK_SUPPLIER_STATE[supplier_name][supplier_sku]["quantity"] = quantity
                MOCK_SUPPLIER_STATE[supplier_name][supplier_sku]["stock_status"] = "OUT_OF_STOCK" if quantity <= 0 else "IN_STOCK"
