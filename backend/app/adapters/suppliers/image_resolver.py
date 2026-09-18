import hashlib
from typing import List, Optional

# High-resolution, brand and category-specific product imagery
IMAGERY_MAP = {
    "laptop": [
        "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=800&auto=format&fit=crop&q=80"
    ],
    "monitor": [
        "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1547082299-de196ea013d6?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1585792180666-f7347c490ee2?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1551645120-d70bfe84c826?w=800&auto=format&fit=crop&q=80"
    ],
    "network": [
        "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1563770660941-20978e870e26?w=800&auto=format&fit=crop&q=80"
    ],
    "storage": [
        "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1628157582853-a796fa650a6a?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&auto=format&fit=crop&q=80"
    ],
    "desktop": [
        "https://images.unsplash.com/photo-1587831990711-23ca6441447b?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1593640408182-31c70c8268f5?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1547082299-de196ea013d6?w=800&auto=format&fit=crop&q=80"
    ],
    "tablet": [
        "https://images.unsplash.com/photo-1561154464-82e9adf32764?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=800&auto=format&fit=crop&q=80"
    ],
    "accessory": [
        "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1541140532154-b024d705b909?w=800&auto=format&fit=crop&q=80"
    ],
    "software": [
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1618060932014-4deda4932554?w=800&auto=format&fit=crop&q=80"
    ]
}

def resolve_product_imagery(
    brand: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    title: Optional[str] = None,
    sku: Optional[str] = None
) -> List[str]:
    """
    Deterministically assigns beautiful, category and brand-specific imagery
    so every product looks distinct, professional, and matching its hardware class.
    """
    text = f"{brand or ''} {category or ''} {subcategory or ''} {title or ''}".lower()

    if any(k in text for k in ["laptop", "notebook", "thinkpad", "elitebook", "probook", "zenbook", "macbook"]):
        group = "laptop"
    elif any(k in text for k in ["monitor", "display", "qhd", "uhd", "led", "screen", "viewsonic", "benq"]):
        group = "monitor"
    elif any(k in text for k in ["switch", "router", "cisco", "catalyst", "network", "firewall", "gateway"]):
        group = "network"
    elif any(k in text for k in ["nas", "storage", "synology", "ssd", "hard drive", "disk", "nvme"]):
        group = "storage"
    elif any(k in text for k in ["tablet", "tab", "ipad", "surface pro"]):
        group = "tablet"
    elif any(k in text for k in ["software", "license", "licensing", "antivirus", "anti-spam", "warranty", "sonicwall"]):
        group = "software"
    elif any(k in text for k in ["desktop", "tower", "sff", "workstation", "z2", "t740"]):
        group = "desktop"
    elif any(k in text for k in ["keyboard", "mouse", "headset", "cable", "dock", "charger", "adapter"]):
        group = "accessory"
    else:
        group = "desktop"

    pool = IMAGERY_MAP.get(group, IMAGERY_MAP["desktop"])
    
    # Deterministic index using hash of SKU or title so each product gets its own consistent image
    key = sku or title or "default"
    idx = int(hashlib.md5(key.encode()).hexdigest(), 16) % len(pool)
    return [pool[idx]]
