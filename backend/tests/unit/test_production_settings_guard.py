from types import SimpleNamespace

from app.core.config import find_insecure_production_settings


def _s(**kw):
    base = dict(ENVIRONMENT="production", SECRET_KEY="x" * 48, FIRST_SUPERUSER_PASSWORD="a-real-strong-password")
    base.update(kw)
    return SimpleNamespace(**base)


def test_development_is_never_blocked():
    assert find_insecure_production_settings(
        _s(ENVIRONMENT="development", SECRET_KEY="dev_secret_key_change_in_production_9f834a81b2c",
           FIRST_SUPERUSER_PASSWORD="adminpassword123")) == []


def test_production_with_real_secrets_is_allowed():
    assert find_insecure_production_settings(_s()) == []


def test_production_rejects_default_signing_key_short_key_and_default_admin_password():
    assert find_insecure_production_settings(_s(SECRET_KEY="dev_secret_key_change_in_production_9f834a81b2c"))
    assert find_insecure_production_settings(_s(SECRET_KEY="short"))
    assert find_insecure_production_settings(_s(FIRST_SUPERUSER_PASSWORD="adminpassword123"))


def test_celery_broker_url_is_honored_for_the_broker():
    """Azure supplies the Redis broker as CELERY_BROKER_URL; it used to be ignored."""
    from app.core.config import Settings
    s = Settings(CELERY_BROKER_URL="rediss://:k@host:10000/0", RABBITMQ_URL="amqp://guest:guest@rabbitmq:5672//")
    assert s.get_rabbitmq_url() == "rediss://:k@host:10000/0"
    assert Settings(CELERY_BROKER_URL=None, RABBITMQ_URL="amqp://x").get_rabbitmq_url() == "amqp://x"
    assert Settings(CELERY_BROKER_URL=None, RABBITMQ_URL=None).get_rabbitmq_url().startswith("amqp://")


def test_cors_is_restricted_to_the_frontend_only_in_production():
    from app.core.config import Settings
    prod = Settings(ENVIRONMENT="production", FRONTEND_URL="https://app.example.com/")
    assert prod.get_cors_origins() == ["https://app.example.com"]
    assert Settings(ENVIRONMENT="production", FRONTEND_URL=None).get_cors_origins() == ["*"]
    assert Settings(ENVIRONMENT="development", FRONTEND_URL="https://app.example.com").get_cors_origins() == ["*"]
