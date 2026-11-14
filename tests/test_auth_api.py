from fastapi.testclient import TestClient

from app.main import app
from app.auth import verify_token

client = TestClient(app)


def test_register_returns_valid_token():
    response = client.post(
        "/register", json={"username": "ngozi", "password": "long-password-1"}
    )

    assert response.status_code == 200
    assert verify_token(response.json()["token"]) is not None


def test_register_duplicate_username():
    body = {"username": "emeka", "password": "long-password-1"}
    client.post("/register", json=body)

    response = client.post("/register", json=body)

    assert response.status_code == 409


def test_login_success_and_failure():
    client.post(
        "/register", json={"username": "funke", "password": "long-password-1"}
    )

    good = client.post(
        "/login", json={"username": "funke", "password": "long-password-1"}
    )
    bad = client.post(
        "/login", json={"username": "funke", "password": "wrong-password-1"}
    )

    assert good.status_code == 200
    assert bad.status_code == 401


def test_short_password_rejected():
    response = client.post(
        "/register", json={"username": "short", "password": "abc"}
    )

    assert response.status_code == 422


def test_tampered_token_rejected():
    assert verify_token("not-a-real-token") is None
