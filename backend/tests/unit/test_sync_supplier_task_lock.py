from unittest.mock import MagicMock, patch

from app.tasks.sync_tasks import sync_supplier_task


def _redis_with_lock(acquired: bool):
    lock = MagicMock()
    lock.acquire.return_value = acquired
    client = MagicMock()
    client.lock.return_value = lock
    return client, lock


def test_overlapping_supplier_sync_is_skipped_not_run():
    """Real incident 2026-11-10: 7 concurrent syncs raced to insert the same new Ma Labs product."""
    client, lock = _redis_with_lock(False)
    with patch("app.services.listing_service.get_redis_client", return_value=client), \
         patch("app.tasks.sync_tasks.SyncService") as svc:
        result = sync_supplier_task.run(7)
    assert result["status"] == "SKIPPED_ALREADY_RUNNING"
    svc.assert_not_called()
    lock.release.assert_not_called()


def test_sync_runs_and_releases_lock_when_acquired():
    client, lock = _redis_with_lock(True)
    with patch("app.services.listing_service.get_redis_client", return_value=client), \
         patch("app.tasks.sync_tasks.SessionLocal"), \
         patch("app.tasks.sync_tasks.SyncService") as svc:
        svc.return_value.sync_supplier.return_value = {"status": "SUCCESSFULLY_SYNCHRONIZED"}
        result = sync_supplier_task.run(7)
    assert result["status"] == "SUCCESSFULLY_SYNCHRONIZED"
    lock.release.assert_called_once()
