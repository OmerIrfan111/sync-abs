import hashlib
import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  NOTE: UPC barcode lookup (upcitemdb.com) has been intentionally    #
#  removed from this module.                                           #
#                                                                      #
#  upcitemdb.com is a consumer product database. B2B wholesale items  #
#  (RF connectors, enterprise networking gear, Cisco licenses, power   #
#  rack equipment, etc.) frequently share UPCs with unrelated consumer #
#  products in that registry, causing completely wrong images to be    #
#  returned (e.g. an iPhone photo for an N-Female SMA Male Connector). #
#                                                                      #
#  Image resolution for this platform uses:                            #
#   1. Supplier API image URL (when the upstream API returns one)       #
#   2. Title + brand keyword classification -> correct hardware group   #
#   3. Curated per-group Unsplash pools (varied per-product by SKU hash)#
# ------------------------------------------------------------------ #


def _validate_url(url):
    """Validates and cleans a supplier-provided image URL."""
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return None
    if url.startswith("http://"):
        url = "https://" + url[7:]
    bad_patterns = ["placeholder", "no_image", "noimage", "default.png", "blank.", "1x1.", "pixel.gif"]
    if any(bad in url.lower() for bad in bad_patterns):
        return None
    return url


# ------------------------------------------------------------------ #
#  Real Ingram Micro / D&H / Synnex category -> hardware group map.  #
#  Built from all distinct category strings observed in the live DB.  #
# ------------------------------------------------------------------ #
CATEGORY_GROUP_MAP = {
    # Ingram Micro
    "computer systems": "laptop",
    "computers desktop": "desktop",
    "displays": "monitor",
    "commercial display": "monitor",
    "network devices": "network",
    "cables": "cable",
    "cables computer & av": "cable",
    "accessories": "accessory",
    "input & output devices": "accessory",
    "storage devices": "storage",
    "cell phones": "phone",
    "mobile accessories": "accessory",
    "computer accessories": "accessory",
    "system components": "component",
    "cases & power supplies": "component",
    "power & rack equipment": "rack",
    "printers & office equipment": "printer",
    "imaging devices": "printer",
    "supplies & media": "accessory",
    "software": "software",
    "software licensing": "software",
    "cisco licenses": "software",
    "services and warranties": "software",
    "communications": "phone",
    "audio/video devices": "av",
    "physical security": "security",
    "security products": "security",
    "data capture / point of sale": "accessory",
    "presentation devices": "av",
    # D&H / Synnex / TD Synnex
    "computers": "laptop",
    "laptops": "laptop",
    "notebooks": "laptop",
    "monitors": "monitor",
    "tablets": "tablet",
    "servers": "server",
    "networking": "network",
    "networking equipment": "network",
    "wireless": "network",
    "hard drives": "storage",
    "solid state drives": "storage",
    "flash storage": "storage",
    "memory": "component",
    "processors": "component",
    "keyboards": "accessory",
    "mice": "accessory",
    "headsets": "accessory",
    "webcams": "accessory",
    "docking stations": "accessory",
    "ups & power protection": "rack",
    "pdus": "rack",
    "kvm switches": "rack",
    "printers": "printer",
    "scanners": "printer",
    "projectors": "av",
    "smartboards": "av",
    "video conferencing": "av",
    "security cameras": "security",
    "access control": "security",
    "point of sale": "accessory",
    "barcode scanners": "accessory",
}

# Keyword-to-group list for fuzzy matching of unknown category strings.
# When a new supplier introduces a category not in CATEGORY_GROUP_MAP above,
# _classify_product scans the raw category string for these keywords.
# This means no code changes are needed when new suppliers are onboarded.
_CATEGORY_KEYWORD_GROUPS = [
    (["laptop", "notebook", "portable"], "laptop"),
    (["desktop", "workstation", "tower", "mini pc"], "desktop"),
    (["monitor", "display", "screen"], "monitor"),
    (["network", "switch", "router", "firewall", "wireless", "wifi", "ethernet"], "network"),
    (["cable", "cord", "wire", "fiber", "connector", "antenna", "rf", "coaxial", "patch",
      "splitter", "coupler", "attenuator", "booster", "amplifier", "coax", "sma", "tnc",
      "rg6", "rg11", "rg58"], "cable"),
    (["storage", "hard drive", "hdd", "nas", "flash drive", "sd card", "usb drive"], "storage"),
    (["ssd", "nvme", "solid state"], "storage"),
    (["tablet", "ipad", "slate"], "tablet"),
    (["phone", "mobile", "smartphone", "cellular"], "phone"),
    (["server", "rack server", "blade"], "server"),
    (["rack", "ups", "pdu", "kvm", "enclosure"], "rack"),
    (["printer", "scanner", "copier", "mfp", "imaging"], "printer"),
    (["software", "license", "subscription", "warranty", "service", "support"], "software"),
    (["projector", "smartboard", "video conf", "av", "audio", "video"], "av"),
    (["camera", "cctv", "surveillance", "security", "badge", "biometric"], "security"),
    (["ram", "ddr", "ddr4", "ddr5", "ddr3", "lpddr", "dimm", "sodimm", "memory module",
      "cpu", "processor", "gpu", "graphics card", "motherboard", "cooling", "fan",
      "component"], "component"),
    (["keyboard", "mouse", "headset", "webcam", "dock", "hub", "charger",
      "stand", "mount", "bag", "sleeve", "accessories"], "accessory"),
]

# These title keywords are so unambiguous that a SINGLE hit overrides any category.
# Used when the category is a broad bucket that commonly receives misc items.
_UNAMBIGUOUS_TITLE_OVERRIDES = {
    "ddr3": "component", "ddr4": "component", "ddr5": "component",
    "lpddr4": "component", "lpddr5": "component",
    "dimm": "component", "sodimm": "component",
    "nvme": "storage", "m.2 ssd": "storage", "pcie ssd": "storage",
    "laserjet": "printer", "inkjet": "printer", "mfp": "printer",
    "poweredge": "server", "proliant": "server",
    "thinkpad": "laptop", "elitebook": "laptop", "latitude": "laptop", "macbook": "laptop",
    "optiplex": "desktop", "thinkcentre": "desktop", "elitedesk": "desktop",
    "surface pro": "tablet", "galaxy tab": "tablet",
    "iphone": "phone",
}


def _classify_product(brand, category, subcategory, title):
    """
    Classifies a product into a hardware image group using a 4-tier strategy:
      1. Exact DB category string lookup (fastest, most accurate)
      2. Exact subcategory string lookup
      3. Fuzzy keyword scan of the raw category string (handles new suppliers)
      4. Title keyword scan (final fallback, catches miscategorized products)

    The title scan is authoritative when the DB category is clearly wrong
    (e.g. Ingram puts RF connectors/antennas/splitters under "Cell Phones").
    """
    cat_lower = (category or "").strip().lower()
    subcat_lower = (subcategory or "").strip().lower()
    title_lower = (title or "").strip().lower()
    brand_lower = (brand or "").strip().lower()

    # Pre-check: unambiguous title terms override everything
    for kw, grp in _UNAMBIGUOUS_TITLE_OVERRIDES.items():
        if kw in title_lower:
            return grp

    # Tier 1: Exact DB category lookup
    group = CATEGORY_GROUP_MAP.get(cat_lower)
    if group:
        # Refine "laptop" by title when it is actually a desktop/server/tablet
        if group == "laptop":
            if any(k in title_lower for k in ["desktop", "tower", "sff", "workstation",
                                               "optiplex", "prodesk", "elitedesk", "thinkcentre",
                                               "imac", "mini pc", "nuc"]):
                return "desktop"
            if any(k in title_lower for k in ["server", "poweredge", "proliant", "rack"]):
                return "server"
            if any(k in title_lower for k in ["tablet", "ipad", "surface go", "galaxy tab"]):
                return "tablet"

        # Title override: when the title strongly contradicts the DB category,
        # trust the title. Handles cases like:
        #   - Ingram placing RF connectors/antennas under "Cell Phones"
        #   - Axiom Memory Solutions placing DDR4 modules under "Cables Computer & AV"
        #   - Ingram placing misc accessories under broad buckets
        for title_keywords, title_grp in _CATEGORY_KEYWORD_GROUPS:
            if title_grp != group and any(kw in title_lower for kw in title_keywords):
                hit_count = sum(1 for kw in title_keywords if kw in title_lower)
                # Override when:
                #   - Title has 2+ keyword hits in a non-matching group, OR
                #   - Category is a broad/miscellaneous bucket that commonly receives misc items
                if hit_count >= 2 or group in ("phone", "accessory", "laptop", "cable"):
                    return title_grp

        return group

    # Tier 2: Subcategory exact lookup
    group = CATEGORY_GROUP_MAP.get(subcat_lower)
    if group:
        return group

    # Tier 3: Fuzzy keyword scan of the raw category string
    for keywords, grp in _CATEGORY_KEYWORD_GROUPS:
        if any(kw in cat_lower for kw in keywords):
            return grp
    if subcat_lower:
        for keywords, grp in _CATEGORY_KEYWORD_GROUPS:
            if any(kw in subcat_lower for kw in keywords):
                return grp

    # Tier 4: Title keyword scan
    text = f"{brand_lower} {cat_lower} {subcat_lower} {title_lower}"
    if any(k in text for k in ["laptop", "notebook", "thinkpad", "elitebook", "probook",
                                "zenbook", "macbook", "chromebook", "latitude", "inspiron",
                                "pavilion", "ideapad", "vivobook", "swift", "predator",
                                "spectre", "envy"]):
        return "laptop"
    if any(k in text for k in ["monitor", "display", "qhd", "uhd", "led monitor",
                                "viewsonic", "benq", "ultrasharp", "curved monitor",
                                "4k monitor"]):
        return "monitor"
    if any(k in text for k in ["switch", "router", "cisco", "catalyst", "network",
                                "firewall", "gateway", "access point", "meraki", "aruba",
                                "unifi", "ethernet", "modem", "wireless ap"]):
        return "network"
    if any(k in text for k in ["cable", "cord", "hdmi cable", "patch cable",
                                "ethernet cable", "displayport", "thunderbolt cable",
                                "usb-c cable", "coax", "connector", "splitter",
                                "antenna", "coupler", "attenuator"]):
        return "cable"
    if any(k in text for k in ["nas", "storage", "synology", "ssd", "hard drive",
                                "disk", "nvme", "hdd", "external drive", "flash drive",
                                "usb drive", "memory card", "sd card"]):
        return "storage"
    if any(k in text for k in ["tablet", "ipad", "surface pro", "surface go",
                                "galaxy tab"]):
        return "tablet"
    if any(k in text for k in ["iphone", "galaxy", "pixel phone", "smartphone",
                                "cell phone", "mobile phone"]):
        return "phone"
    if any(k in text for k in ["software", "license", "licensing", "antivirus",
                                "anti-spam", "warranty", "subscription", "office 365",
                                "windows", "endpoint protection", "cisco lic"]):
        return "software"
    if any(k in text for k in ["desktop", "tower", "sff", "workstation", "thinkcentre",
                                "optiplex", "prodesk", "elitedesk", "imac", "mini pc",
                                "nuc"]):
        return "desktop"
    if any(k in text for k in ["printer", "print", "laserjet", "inkjet", "scanner",
                                "copier", "plotter", "mfp"]):
        return "printer"
    if any(k in text for k in ["server", "poweredge", "proliant", "rack unit",
                                "blade server"]):
        return "server"
    if any(k in text for k in ["rack", "pdu", "ups", "power strip", "kvm",
                                "patch panel"]):
        return "rack"
    if any(k in text for k in ["projector", "smartboard", "video conf", "audio",
                                "video conference", "presentation", "hdmi splitter"]):
        return "av"
    if any(k in text for k in ["camera", "cctv", "surveillance", "security camera",
                                "badge reader"]):
        return "security"
    if any(k in text for k in ["keyboard", "mouse", "headset", "dock", "charger",
                                "adapter", "hub", "webcam", "speaker", "microphone",
                                "stand", "mount", "bag", "sleeve", "battery"]):
        return "accessory"
    if any(k in text for k in ["ram", "ddr", "memory", "cpu", "processor", "gpu",
                                "graphics card", "motherboard", "cooling", "fan"]):
        return "component"

    return "accessory"


# ------------------------------------------------------------------ #
#  Per-group curated image pools.                                     #
#  All URLs are verified to show the correct hardware category.       #
# ------------------------------------------------------------------ #
CATEGORY_IMAGES: Dict[str, List[str]] = {
    "laptop": [
        "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=600&auto=format&fit=crop&q=80",
    ],
    "desktop": [
        "https://images.unsplash.com/photo-1587831990711-23ca6441447b?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1593640408182-31c70c8268f5?w=600&auto=format&fit=crop&q=80",
    ],
    "monitor": [
        "https://images.unsplash.com/photo-1585792180666-f7347c490ee2?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1616469829941-c7200edec809?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1551645120-d70bfe84c826?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1517059224940-d4af9eec41b7?w=600&auto=format&fit=crop&q=80",
    ],
    "network": [
        "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1563770660941-20978e870e26?w=600&auto=format&fit=crop&q=80",
    ],
    "cable": [
        "https://images.unsplash.com/photo-1601524909162-ae8725290836?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1605339837222-6b5e4be21b4f?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1519558260268-cde7e03a0152?w=600&auto=format&fit=crop&q=80",
    ],
    "storage": [
        "https://images.unsplash.com/photo-1531492746076-161ca9bcad58?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1618410319051-df6d9f6b8ab9?w=600&auto=format&fit=crop&q=80",
    ],
    "tablet": [
        "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1561154464-82e9adf32764?w=600&auto=format&fit=crop&q=80",
    ],
    "phone": [
        "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1592950630581-03cb41342cc5?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1580910051074-3eb694886505?w=600&auto=format&fit=crop&q=80",
    ],
    "software": [
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1618060932014-4deda4932554?w=600&auto=format&fit=crop&q=80",
    ],
    "printer": [
        "https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1586953208448-b95a79798f07?w=600&auto=format&fit=crop&q=80",
    ],
    "server": [
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1591488320449-011701bb6704?w=600&auto=format&fit=crop&q=80",
    ],
    "rack": [
        "https://images.unsplash.com/photo-1591488320449-011701bb6704?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600&auto=format&fit=crop&q=80",
    ],
    "component": [
        "https://images.unsplash.com/photo-1555617981-dac3880eac6e?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1541029071515-84cc54f84dc5?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1628157582853-a796fa650a6a?w=600&auto=format&fit=crop&q=80",
    ],
    "accessory": [
        "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1527814050087-3793815479db?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1595225476474-87563907a212?w=600&auto=format&fit=crop&q=80",
    ],
    "av": [
        "https://images.unsplash.com/photo-1585521551653-a45ce45e0c49?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&auto=format&fit=crop&q=80",
    ],
    "security": [
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1551808525-51a94da548ce?w=600&auto=format&fit=crop&q=80",
    ],
}

# Brand-specific overrides for verified correct photos
BRAND_IMAGES: Dict[str, Dict[str, List[str]]] = {
    "hp": {
        "laptop": ["https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?w=600&auto=format&fit=crop&q=80"],
        "desktop": ["https://images.unsplash.com/photo-1587831990711-23ca6441447b?w=600&auto=format&fit=crop&q=80"],
        "printer": ["https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=600&auto=format&fit=crop&q=80"],
    },
    "dell": {
        "laptop": [
            "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&auto=format&fit=crop&q=80",
        ],
        "desktop": ["https://images.unsplash.com/photo-1593640408182-31c70c8268f5?w=600&auto=format&fit=crop&q=80"],
        "monitor": ["https://images.unsplash.com/photo-1585792180666-f7347c490ee2?w=600&auto=format&fit=crop&q=80"],
    },
    "apple": {
        "laptop": [
            "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?w=600&auto=format&fit=crop&q=80",
        ],
        "tablet": ["https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop&q=80"],
        "desktop": ["https://images.unsplash.com/photo-1527443154391-507e9dc6c5cc?w=600&auto=format&fit=crop&q=80"],
        "phone": ["https://images.unsplash.com/photo-1580910051074-3eb694886505?w=600&auto=format&fit=crop&q=80"],
    },
    "cisco": {
        "network": [
            "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=600&auto=format&fit=crop&q=80",
        ],
        "software": ["https://images.unsplash.com/photo-1563986768609-322da13575f3?w=600&auto=format&fit=crop&q=80"],
    },
    "logitech": {
        "accessory": [
            "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1527814050087-3793815479db?w=600&auto=format&fit=crop&q=80",
        ],
    },
    "microsoft": {
        "laptop": ["https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?w=600&auto=format&fit=crop&q=80"],
        "software": ["https://images.unsplash.com/photo-1618060932014-4deda4932554?w=600&auto=format&fit=crop&q=80"],
    },
    "lenovo": {
        "laptop": [
            "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&auto=format&fit=crop&q=80",
        ],
        "desktop": ["https://images.unsplash.com/photo-1587831990711-23ca6441447b?w=600&auto=format&fit=crop&q=80"],
    },
    "samsung": {
        "monitor": ["https://images.unsplash.com/photo-1585792180666-f7347c490ee2?w=600&auto=format&fit=crop&q=80"],
        "phone": ["https://images.unsplash.com/photo-1592950630581-03cb41342cc5?w=600&auto=format&fit=crop&q=80"],
    },
    "asus": {
        "laptop": ["https://images.unsplash.com/photo-1588702547919-26089e690ecc?w=600&auto=format&fit=crop&q=80"],
        "monitor": ["https://images.unsplash.com/photo-1585792180666-f7347c490ee2?w=600&auto=format&fit=crop&q=80"],
    },
    "acer": {
        "laptop": ["https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=600&auto=format&fit=crop&q=80"],
        "monitor": ["https://images.unsplash.com/photo-1551645120-d70bfe84c826?w=600&auto=format&fit=crop&q=80"],
    },
    "anker": {
        "accessory": ["https://images.unsplash.com/photo-1595225476474-87563907a212?w=600&auto=format&fit=crop&q=80"],
        "cable": ["https://images.unsplash.com/photo-1601524909162-ae8725290836?w=600&auto=format&fit=crop&q=80"],
    },
    "wilson": {
        "cable": ["https://images.unsplash.com/photo-1601524909162-ae8725290836?w=600&auto=format&fit=crop&q=80"],
        "accessory": ["https://images.unsplash.com/photo-1595225476474-87563907a212?w=600&auto=format&fit=crop&q=80"],
    },
}


def resolve_product_imagery(
    brand=None,
    category=None,
    subcategory=None,
    title=None,
    sku=None,
    upc=None,       # Accepted for API compatibility but deliberately ignored
    supplier_image_url=None,
):
    """
    Resolves up to 3 product image URLs in priority order:
      1. Supplier-provided image URL (validated)
      2. Brand-specific curated pool for the detected hardware group
      3. Category pool (varied by SKU hash for visual variety)

    The upc parameter is accepted for backwards compatibility but is never
    used. See the module-level note for why UPC lookup was removed.
    """
    results: List[str] = []

    # Tier 1: Supplier-provided image URL
    validated = _validate_url(supplier_image_url)
    if validated:
        results.append(validated)

    # Classify the product into a hardware group
    brand_clean = (brand or "").strip().lower()
    cat_clean = (category or "").strip().lower()
    subcat_clean = (subcategory or "").strip().lower()
    title_clean = (title or "").strip()
    group = _classify_product(brand_clean, cat_clean, subcat_clean, title_clean.lower())

    # Tiers 2 & 3: Brand pool then category pool, deduplicated, varied by SKU hash
    key = str(sku or title or "default")
    base_idx = int(hashlib.md5(key.encode()).hexdigest(), 16)

    brand_key = brand_clean.split()[0] if brand_clean else ""
    brand_pool = BRAND_IMAGES.get(brand_key, {}).get(group, [])
    cat_pool = CATEGORY_IMAGES.get(group, CATEGORY_IMAGES.get("accessory", []))

    combined: List[str] = []
    seen: set = set()
    for url in list(brand_pool) + list(cat_pool):
        if url not in seen:
            combined.append(url)
            seen.add(url)

    needed = 3 - len(results)
    for offset in range(needed):
        if not combined:
            break
        candidate = combined[(base_idx + offset) % len(combined)]
        if candidate not in results:
            results.append(candidate)

    if not results:
        results.append(
            "https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?w=600&auto=format&fit=crop&q=80"
        )

    return results


def resolve_image_by_upc_with_title_verification(
    product,
    threshold: Optional[float] = None,
    provider=None
):
    """
    Feature 4 entry point: Resolves image by searching candidate images via UPC,
    verifying title/brand similarity using the shared matcher, and attaching
    only if passing threshold. Marks 'image_needs_review' on failure.
    """
    from app.services.image_matching_service import ImageMatchingService
    service = ImageMatchingService(provider=provider)
    return service.match_product_image_by_upc(product, threshold=threshold, save_db=False)