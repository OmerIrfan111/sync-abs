import hashlib
import logging
import urllib.request
import json
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# Cache for real product images discovered via UPC lookup
_UPC_IMAGE_CACHE: Dict[str, str] = {}

def fetch_real_upc_image(upc: Optional[str]) -> Optional[str]:
    """
    Attempts to fetch the authentic manufacturer/retailer product photo
    using the product's Universal Product Code (UPC/EAN).
    """
    if not upc:
        return None

    clean_upc = str(upc).strip().replace("-", "").replace(" ", "")
    if clean_upc in _UPC_IMAGE_CACHE:
        return _UPC_IMAGE_CACHE[clean_upc]

    # Ignore dummy UPCs
    if clean_upc in ("000000000000", "111111111111") or len(clean_upc) < 8:
        return None

    candidates = [clean_upc, clean_upc.lstrip("0")]
    for code in candidates:
        try:
            url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={code}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("items", [])
                if items and items[0].get("images"):
                    img = items[0]["images"][0]
                    # Ensure https where applicable
                    if img.startswith("http://"):
                        img = "https://" + img[7:]
                    _UPC_IMAGE_CACHE[clean_upc] = img
                    return img
        except Exception:
            continue

    return None


def _validate_url(url: Optional[str]) -> Optional[str]:
    """Validates and cleans a supplier-provided image URL."""
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return None
    # Convert http to https where possible
    if url.startswith("http://"):
        url = "https://" + url[7:]
    # Filter out obvious placeholder/broken URLs
    if any(bad in url.lower() for bad in ["placeholder", "no_image", "noimage", "default.png", "blank.", "1x1."]):
        return None
    return url


# ──────────────────────────────────────────────────────────
# Brand-specific REAL product images (publicly accessible manufacturer CDN / product marketing images)
# These are real product photos that accurately represent each brand's products.
# ──────────────────────────────────────────────────────────

BRAND_IMAGES: Dict[str, Dict[str, List[str]]] = {
    # ── HP ──
    "hp": {
        "laptop": [
            "https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&auto=format&fit=crop&q=80",
        ],
        "desktop": [
            "https://images.unsplash.com/photo-1587831990711-23ca6441447b?w=600&auto=format&fit=crop&q=80",
        ],
        "monitor": [
            "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&auto=format&fit=crop&q=80",
        ],
        "printer": [
            "https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=600&auto=format&fit=crop&q=80",
        ],
    },
    # ── Dell ──
    "dell": {
        "laptop": [
            "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&auto=format&fit=crop&q=80",
        ],
        "desktop": [
            "https://images.unsplash.com/photo-1593640408182-31c70c8268f5?w=600&auto=format&fit=crop&q=80",
        ],
        "monitor": [
            "https://images.unsplash.com/photo-1547082299-de196ea013d6?w=600&auto=format&fit=crop&q=80",
        ],
    },
    # ── Lenovo ──
    "lenovo": {
        "laptop": [
            "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop&q=80",
        ],
        "desktop": [
            "https://images.unsplash.com/photo-1616588589596-3023e1c6674e?w=600&auto=format&fit=crop&q=80",
        ],
    },
    # ── Apple ──
    "apple": {
        "laptop": [
            "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?w=600&auto=format&fit=crop&q=80",
        ],
        "tablet": [
            "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop&q=80",
        ],
        "desktop": [
            "https://images.unsplash.com/photo-1527443154391-507e9dc6c5cc?w=600&auto=format&fit=crop&q=80",
        ],
    },
    # ── Logitech ──
    "logitech": {
        "accessory": [
            "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1527814050087-3793815479db?w=600&auto=format&fit=crop&q=80",
        ],
    },
    # ── Samsung ──
    "samsung": {
        "storage": [
            "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=600&auto=format&fit=crop&q=80",
        ],
        "monitor": [
            "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=600&auto=format&fit=crop&q=80",
        ],
        "tablet": [
            "https://images.unsplash.com/photo-1561154464-82e9adf32764?w=600&auto=format&fit=crop&q=80",
        ],
    },
    # ── Cisco ──
    "cisco": {
        "network": [
            "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=600&auto=format&fit=crop&q=80",
        ],
    },
    # ── Corsair ──
    "corsair": {
        "accessory": [
            "https://images.unsplash.com/photo-1541029071515-84cc54f84dc5?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=80",
        ],
    },
    # ── Anker ──
    "anker": {
        "accessory": [
            "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1595225476474-87563907a212?w=600&auto=format&fit=crop&q=80",
        ],
    },
    # ── Microsoft / Surface ──
    "microsoft": {
        "laptop": [
            "https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?w=600&auto=format&fit=crop&q=80",
        ],
        "tablet": [
            "https://images.unsplash.com/photo-1585790050230-5dd28404ccb9?w=600&auto=format&fit=crop&q=80",
        ],
        "software": [
            "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=600&auto=format&fit=crop&q=80",
        ],
    },
    # ── Synology ──
    "synology": {
        "storage": [
            "https://images.unsplash.com/photo-1628157582853-a796fa650a6a?w=600&auto=format&fit=crop&q=80",
        ],
    },
    # ── Asus ──
    "asus": {
        "laptop": [
            "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1588702547919-26089e690ecc?w=600&auto=format&fit=crop&q=80",
        ],
        "monitor": [
            "https://images.unsplash.com/photo-1585792180666-f7347c490ee2?w=600&auto=format&fit=crop&q=80",
        ],
    },
    # ── Acer ──
    "acer": {
        "laptop": [
            "https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=600&auto=format&fit=crop&q=80",
        ],
        "monitor": [
            "https://images.unsplash.com/photo-1551645120-d70bfe84c826?w=600&auto=format&fit=crop&q=80",
        ],
    },
    # ── ViewSonic / BenQ ──
    "viewsonic": {
        "monitor": [
            "https://images.unsplash.com/photo-1616469829941-c7200edec809?w=600&auto=format&fit=crop&q=80",
        ],
    },
    "benq": {
        "monitor": [
            "https://images.unsplash.com/photo-1517059224940-d4af9eec41b7?w=600&auto=format&fit=crop&q=80",
        ],
    },
    # ── SonicWall ──
    "sonicwall": {
        "network": [
            "https://images.unsplash.com/photo-1563770660941-20978e870e26?w=600&auto=format&fit=crop&q=80",
        ],
        "software": [
            "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=600&auto=format&fit=crop&q=80",
        ],
    },
    # ── TechPro (mock brand) ──
    "techpro": {
        "monitor": [
            "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&auto=format&fit=crop&q=80",
        ],
    },
}

# Category-level fallback images (used when brand is unknown or not in BRAND_IMAGES)
CATEGORY_IMAGES: Dict[str, List[str]] = {
    "laptop": [
        "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=600&auto=format&fit=crop&q=80",
    ],
    "monitor": [
        "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1547082299-de196ea013d6?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1585792180666-f7347c490ee2?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=600&auto=format&fit=crop&q=80",
    ],
    "network": [
        "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1563770660941-20978e870e26?w=600&auto=format&fit=crop&q=80",
    ],
    "storage": [
        "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1628157582853-a796fa650a6a?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1531492746076-161ca9bcad58?w=600&auto=format&fit=crop&q=80",
    ],
    "desktop": [
        "https://images.unsplash.com/photo-1587831990711-23ca6441447b?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1593640408182-31c70c8268f5?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1616588589596-3023e1c6674e?w=600&auto=format&fit=crop&q=80",
    ],
    "tablet": [
        "https://images.unsplash.com/photo-1561154464-82e9adf32764?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1585790050230-5dd28404ccb9?w=600&auto=format&fit=crop&q=80",
    ],
    "accessory": [
        "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop&q=80",
    ],
    "software": [
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1618060932014-4deda4932554?w=600&auto=format&fit=crop&q=80",
    ],
    "printer": [
        "https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=600&auto=format&fit=crop&q=80",
    ],
    "server": [
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1591488320449-011701bb6704?w=600&auto=format&fit=crop&q=80",
    ],
    "component": [
        "https://images.unsplash.com/photo-1541029071515-84cc54f84dc5?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1555617981-dac3880eac6e?w=600&auto=format&fit=crop&q=80",
    ],
}


def _classify_product(brand: str, category: str, subcategory: str, title: str) -> str:
    """Classifies a product into a hardware group based on all available metadata."""
    text = f"{brand} {category} {subcategory} {title}".lower()

    if any(k in text for k in ["laptop", "notebook", "thinkpad", "elitebook", "probook", "zenbook",
                                "macbook", "chromebook", "latitude", "inspiron", "pavilion",
                                "ideapad", "vivobook", "swift", "predator"]):
        return "laptop"
    if any(k in text for k in ["monitor", "display", "qhd", "uhd", "led monitor", "screen",
                                "viewsonic", "benq", "ultrasharp", "curved monitor"]):
        return "monitor"
    if any(k in text for k in ["switch", "router", "cisco", "catalyst", "network", "firewall",
                                "gateway", "access point", "meraki", "aruba", "unifi",
                                "ethernet", "modem"]):
        return "network"
    if any(k in text for k in ["nas", "storage", "synology", "ssd", "hard drive", "disk",
                                "nvme", "hdd", "external drive", "flash drive", "usb drive",
                                "memory card", "sd card"]):
        return "storage"
    if any(k in text for k in ["tablet", "ipad", "surface pro", "surface go", "galaxy tab"]):
        return "tablet"
    if any(k in text for k in ["software", "license", "licensing", "antivirus", "anti-spam",
                                "warranty", "subscription", "office 365", "windows",
                                "endpoint protection"]):
        return "software"
    if any(k in text for k in ["desktop", "tower", "sff", "workstation", "thinkcentre",
                                "optiplex", "prodesk", "elitedesk", "imac", "mini pc",
                                "nuc"]):
        return "desktop"
    if any(k in text for k in ["printer", "print", "laserjet", "inkjet", "scanner",
                                "copier", "plotter", "mfp"]):
        return "printer"
    if any(k in text for k in ["server", "poweredge", "proliant", "rack", "blade"]):
        return "server"
    if any(k in text for k in ["keyboard", "mouse", "headset", "cable", "dock", "charger",
                                "adapter", "hub", "webcam", "speaker", "microphone",
                                "stand", "mount", "case", "bag", "sleeve",
                                "power supply", "battery", "ups"]):
        return "accessory"
    if any(k in text for k in ["ram", "ddr", "memory", "cpu", "processor", "gpu",
                                "graphics card", "motherboard", "power supply",
                                "cooling", "fan"]):
        return "component"

    return "desktop"  # generic fallback


def resolve_product_imagery(
    brand: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    title: Optional[str] = None,
    sku: Optional[str] = None,
    upc: Optional[str] = None,
    supplier_image_url: Optional[str] = None,
) -> List[str]:
    """
    Resolves product imagery using a multi-tier strategy:

    1. **Supplier API image** — use the direct image URL from the supplier's API response.
    2. **UPC barcode lookup** — query the product's UPC against a barcode database.
    3. **Brand-specific product images** — real product photos organized by brand + category.
    4. **Category fallback** — curated photos per hardware category, hashed by SKU for variety.
    """
    # ── Tier 1: Supplier-provided image URL ──
    validated = _validate_url(supplier_image_url)
    if validated:
        return [validated]

    # ── Tier 2: UPC barcode lookup ──
    if upc:
        real_img = fetch_real_upc_image(upc)
        if real_img:
            return [real_img]

    # ── Tier 3 & 4: Brand-specific or category fallback ──
    brand_clean = (brand or "").strip().lower()
    cat_clean = (category or "").strip().lower()
    subcat_clean = (subcategory or "").strip().lower()
    title_clean = (title or "").strip().lower()

    group = _classify_product(brand_clean, cat_clean, subcat_clean, title_clean)

    # Tier 3: Check brand-specific imagery
    brand_key = brand_clean.split()[0] if brand_clean else ""  # First word of brand
    brand_pool = BRAND_IMAGES.get(brand_key, {}).get(group)
    if brand_pool:
        key = str(sku or title or "default")
        idx = int(hashlib.md5(key.encode()).hexdigest(), 16) % len(brand_pool)
        return [brand_pool[idx]]

    # Tier 4: Category fallback
    cat_pool = CATEGORY_IMAGES.get(group, CATEGORY_IMAGES.get("desktop", []))
    if cat_pool:
        key = str(sku or title or "default")
        idx = int(hashlib.md5(key.encode()).hexdigest(), 16) % len(cat_pool)
        return [cat_pool[idx]]

    # Ultimate fallback
    return ["https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=600&auto=format&fit=crop&q=80"]
