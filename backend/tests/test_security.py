"""Authentication and authorization behavior that does not need a database."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.core.security import AUDIENCE, ISSUER, create_access_token, decode_access_token, hash_password, verify_password
from app.core.settings import get_settings
from app.db.models import User
from app.db.session import get_session
from app.main import app


def test_password_hash_and_jwt_reject_tampering() -> None:
    settings = get_settings()
    user_id = uuid.uuid4()
    encoded = create_access_token(user_id, settings)

    assert decode_access_token(encoded, settings) == user_id
    assert verify_password("a long test password", hash_password("a long test password"))
    assert not verify_password("wrong password", hash_password("a long test password"))

    tampered = jwt.encode(
        {"sub": str(user_id), "iss": ISSUER, "aud": AUDIENCE, "iat": 1, "exp": 4102444800},
        "wrong-signing-secret-that-is-long-enough",
        algorithm="HS256",
    )
    try:
        decode_access_token(tampered, settings)
    except ValueError:
        pass
    else:
        raise AssertionError("A token signed with another secret must be rejected")

    expired = jwt.encode(
        {
            "sub": str(user_id), "iss": ISSUER, "aud": AUDIENCE,
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    try:
        decode_access_token(expired, settings)
    except ValueError:
        pass
    else:
        raise AssertionError("An expired token must be rejected")


def test_health_is_public_but_assets_require_authentication() -> None:
    with TestClient(app) as client:
        assert client.get("/api/v1/health/live").json() == {"status": "ok"}
        response = client.get("/api/v1/installations")
        assert response.status_code == 401


def test_viewer_cannot_create_installations() -> None:
    viewer = User(
        id=uuid.uuid4(), email="viewer@example.com", password_hash="unused",
        full_name="Viewer", role="viewer", is_active=True,
    )

    def fake_session():
        yield object()

    app.dependency_overrides[get_current_user] = lambda: viewer
    app.dependency_overrides[get_session] = fake_session
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/installations",
                json={"code": "MINE-1", "name": "Mine 1", "kind": "mine"},
            )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_login_checks_password_and_returns_usable_token() -> None:
    user = User(
        id=uuid.uuid4(), email="operator@example.com",
        password_hash=hash_password("correct-test-password"),
        full_name="Operator", role="operator", is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    class FakeSession:
        def scalar(self, query):
            return user

        def get(self, model, key):
            return user if key == user.id else None

    def fake_session():
        yield FakeSession()

    app.dependency_overrides[get_session] = fake_session
    try:
        with TestClient(app) as client:
            ok = client.post(
                "/api/v1/auth/login",
                data={"username": user.email, "password": "correct-test-password"},
            )
            bad = client.post(
                "/api/v1/auth/login",
                data={"username": user.email, "password": "wrong-password"},
            )
            profile = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {ok.json()['access_token']}"},
            )
        assert ok.status_code == 200
        assert bad.status_code == 401
        assert profile.status_code == 200
        assert profile.json()["email"] == user.email
    finally:
        app.dependency_overrides.clear()
