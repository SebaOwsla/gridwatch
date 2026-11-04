"""Focused checks for host, browser-origin and SQL injection boundaries."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.models import User
from app.db.session import get_session
from app.main import app


@pytest.mark.parametrize("injected_email", [
    "admin' OR '1'='1'--",
    "x'; DROP TABLE users; --",
    "' UNION SELECT password_hash FROM users --",
])
def test_login_treats_injection_strings_as_bound_data(injected_email: str) -> None:
    statements = []

    class EmptySession:
        def scalar(self, statement):
            statements.append(statement)
            return None

    def fake_session():
        yield EmptySession()

    app.dependency_overrides[get_session] = fake_session
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/auth/login", data={
                "username": injected_email, "password": "wrong-password",
            })
        assert response.status_code == 401
        assert len(statements) == 1
        compiled = statements[0].compile(dialect=postgresql.dialect())
        assert injected_email.lower() in compiled.params.values()
        assert injected_email not in str(compiled)
    finally:
        app.dependency_overrides.clear()


def test_sql_injection_cannot_bypass_login_or_drop_users_table() -> None:
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.__table__.create(engine)
    with Session(engine) as session:
        session.add(User(email="admin@gridwatch.local", full_name="Admin", role="admin",
                         password_hash=hash_password("valid-test-password")))
        session.commit()

    def sqlite_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = sqlite_session
    try:
        with TestClient(app) as client:
            for username in (
                "admin@gridwatch.local' OR '1'='1'--",
                "x'; DROP TABLE users; --",
            ):
                response = client.post("/api/v1/auth/login", data={
                    "username": username, "password": "valid-test-password",
                })
                assert response.status_code == 401
            valid = client.post("/api/v1/auth/login", data={
                "username": "admin@gridwatch.local", "password": "valid-test-password",
            })
            assert valid.status_code == 200
            assert valid.json()["token_type"] == "bearer"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_host_origin_and_security_headers() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert response.headers["Cache-Control"] == "no-store"

        bad_host = client.get("/api/v1/health/live", headers={"Host": "attacker.example"})
        assert bad_host.status_code == 400

        bad_origin = client.options("/api/v1/auth/login", headers={
            "Origin": "https://attacker.example", "Access-Control-Request-Method": "POST",
        })
        assert bad_origin.status_code == 400
        assert "Access-Control-Allow-Origin" not in bad_origin.headers
