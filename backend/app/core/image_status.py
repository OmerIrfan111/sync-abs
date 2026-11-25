from typing import Iterable, List, Optional
from urllib.parse import urlparse

# Generic stock photos from image_resolver's curated pools. They are display
# placeholders only: they show a *kind* of product (a laptop, a cable), never
# the actual item, so they must never be treated as a real product photo or
# sent to a live marketplace listing.
PLACEHOLDER_HOSTS = ("images.unsplash.com",)

# image_status values (stored in Product.specs_json["image_status"]) that mean
# the stored image is a real photo of this exact product.
REAL_IMAGE_STATUSES = ("icecat", "supplier", "verified", "manual")

IMAGE_RECHECK_DAYS = 7


def is_placeholder_url(url: Optional[str]) -> bool:
    if not url or not isinstance(url, str):
        return True
    host = (urlparse(url.strip()).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in PLACEHOLDER_HOSTS)


def real_images(images: Optional[Iterable[str]]) -> List[str]:
    return [u for u in (images or []) if isinstance(u, str) and not is_placeholder_url(u)]


def has_real_image(product) -> bool:
    return bool(real_images(getattr(product, "images", None)))
