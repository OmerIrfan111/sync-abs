from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from app.services.listing_service import ListingService


@contextmanager
def _unavailable_lock(lock_key, timeout_seconds=10):
    """Simulates distributed_lock() failing to acquire the real Redis lock."""
    yield False


def test_withdraw_listing_from_marketplace_raises_when_lock_not_acquired():
    """
    Real bug fixed 2026-10-22: withdraw_listing_from_marketplace() entered
    the `with distributed_lock(...) as acquired:` block but never checked
    `acquired`, unlike publish_product_to_marketplace() (which does, right
    above). Under real lock contention between two Celery workers racing
    on the same listing, this let the withdraw proceed completely
    unprotected, defeating the "duplicate-update prevention" the lock
    exists for. It must raise instead of silently continuing.
    """
    service = ListingService(MagicMock())
    with patch("app.services.listing_service.distributed_lock", _unavailable_lock):
        with pytest.raises(RuntimeError, match="Could not acquire distributed lock"):
            service.withdraw_listing_from_marketplace(listing_id=1)


def test_reactivate_listing_on_marketplace_raises_when_lock_not_acquired():
    service = ListingService(MagicMock())
    with patch("app.services.listing_service.distributed_lock", _unavailable_lock):
        with pytest.raises(RuntimeError, match="Could not acquire distributed lock"):
            service.reactivate_listing_on_marketplace(listing_id=1)
