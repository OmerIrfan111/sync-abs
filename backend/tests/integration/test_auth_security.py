from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password
from app.main import app
from app.models.user import User


class FakeRedis:
    def __init__(self):
        self.data, self.ttls = {}, {}

    def get(self, k):
        return self.data.get(k)

    def incr(self, k):
        self.data[k] = int(self.data.get(k, 0)) + 1
        return self.data[k]

    def expire(self, k, s):
        self.ttls[k] = s

    def ttl(self, k):
        return self.ttls.get(k, -1)

    def delete(self, k):
        self.data.pop(k, None)


def _make_user(db, email="staff-test@example.com", password="tpw@1"):
    u = User(email=email, hashed_password=get_password_hash(password), full_name="Staff", role="operator",
             is_active=True, is_superuser=False)
    db.add(u)
    db.commit()
    return u


def _login_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


def test_staff_can_log_in_with_a_short_password_and_is_not_an_admin(db_session, monkeypatch):
    monkeypatch.setattr("app.core.login_throttle._redis", lambda: None)
    _make_user(db_session)
    c = _login_client(db_session)
    res = c.post("/api/v1/auth/login/json", json={"email": "staff-test@example.com", "password": "tpw@1"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = c.get("/api/v1/auth/me", headers=headers).json()
    assert me["role"] == "operator" and me["is_superuser"] is False
    assert c.put("/api/v1/orders/auto-order", json={"enabled": True}, headers=headers).status_code == 403


def test_five_wrong_passwords_lock_the_account_even_for_the_right_password(db_session, monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr("app.core.login_throttle._redis", lambda: fake)
    _make_user(db_session)
    c = _login_client(db_session)
    for _ in range(5):
        assert c.post("/api/v1/auth/login/json", json={"email": "staff-test@example.com", "password": "wrong"}).status_code == 400
    locked = c.post("/api/v1/auth/login/json", json={"email": "staff-test@example.com", "password": "tpw@1"})
    assert locked.status_code == 429 and "locked" in locked.json()["detail"]


def test_a_successful_login_clears_earlier_failures(db_session, monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr("app.core.login_throttle._redis", lambda: fake)
    _make_user(db_session)
    c = _login_client(db_session)
    for _ in range(3):
        c.post("/api/v1/auth/login/json", json={"email": "staff-test@example.com", "password": "wrong"})
    assert c.post("/api/v1/auth/login/json", json={"email": "staff-test@example.com", "password": "tpw@1"}).status_code == 200
    assert fake.data == {}


def test_login_still_works_when_redis_is_down(db_session, monkeypatch):
    monkeypatch.setattr("app.core.login_throttle._redis", lambda: None)
    _make_user(db_session)
    c = _login_client(db_session)
    assert c.post("/api/v1/auth/login/json", json={"email": "staff-test@example.com", "password": "tpw@1"}).status_code == 200


def test_user_can_change_their_own_password(db_session):
    user = _make_user(db_session)
    app.dependency_overrides[get_current_user] = lambda: user
    c = _login_client(db_session)
    res = c.post("/api/v1/auth/change-password", json={"current_password": "tpw@1", "new_password": "a-much-better-pass"})
    assert res.status_code == 200
    db_session.refresh(user)
    assert verify_password("a-much-better-pass", user.hashed_password)
    assert not verify_password("tpw@1", user.hashed_password)


def test_change_password_rejects_wrong_current_short_and_unchanged(db_session):
    user = _make_user(db_session)
    app.dependency_overrides[get_current_user] = lambda: user
    c = _login_client(db_session)
    assert c.post("/api/v1/auth/change-password", json={"current_password": "nope", "new_password": "a-much-better-pass"}).status_code == 400
    assert c.post("/api/v1/auth/change-password", json={"current_password": "tpw@1", "new_password": "short"}).status_code == 422
    assert c.post("/api/v1/auth/change-password", json={"current_password": "tpw@1", "new_password": "tpw@1"}).status_code in (400, 422)
    db_session.refresh(user)
    assert verify_password("tpw@1", user.hashed_password)
