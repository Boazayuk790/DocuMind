from fastapi.testclient import TestClient

from app.main import app


def test_login_is_rate_limited():
    client = TestClient(app)
    body = {"username": "nobody", "password": "wrong-password"}

    for _ in range(5):
        assert client.post("/login", json=body).status_code == 401

    response = client.post("/login", json=body)

    assert response.status_code == 429
    assert "retry-after" in response.headers


def test_register_is_rate_limited():
    client = TestClient(app)

    for i in range(5):
        response = client.post("/register", json={
            "username": f"limituser{i}",
            "password": "long-enough-pw"
        })
        assert response.status_code == 200

    response = client.post("/register", json={
        "username": "limituser-extra",
        "password": "long-enough-pw"
    })

    assert response.status_code == 429