import pytest
from app.auth.service import hash_password, verify_password, create_user, authenticate
from app.auth.jwt_utils import create_token, decode_token


def test_password_hash_roundtrip():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_roundtrip():
    token = create_token("user-id-123", "test@example.com")
    payload = decode_token(token)
    assert payload["sub"] == "user-id-123"
    assert payload["email"] == "test@example.com"


def test_create_user_and_authenticate(db_session):
    user = create_user(db_session, "u@example.com", "pw12345")
    assert user.email == "u@example.com"
    assert user.id is not None

    authed = authenticate(db_session, "u@example.com", "pw12345")
    assert authed is not None
    assert authed.id == user.id

    assert authenticate(db_session, "u@example.com", "wrong") is None
    assert authenticate(db_session, "missing@example.com", "pw12345") is None


def test_register_and_login_endpoints(client):
    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "secretpass"})
    assert r.status_code == 200
    assert "token" in r.json()

    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "secretpass"})
    assert r.status_code == 200
    assert "token" in r.json()

    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "wrong"})
    assert r.status_code == 401
