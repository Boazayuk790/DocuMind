import pytest

import app.database as database


@pytest.fixture(autouse=True)
def temporary_database(tmp_path, monkeypatch):
    monkeypatch.setattr(
        database, "DATABASE_PATH", tmp_path / "test_documind.db"
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database.initialize_database()


@pytest.fixture(autouse=True)
def secret_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")


@pytest.fixture
def user_id():
    return database.register_user("tester", "test-password-1")


@pytest.fixture
def auth_headers(user_id):
    from app.auth import create_token
    return {"Authorization": f"Bearer {create_token(user_id)}"}


@pytest.fixture(autouse=True)
def reset_rate_limits():
    from app import rate_limit
    rate_limit.reset()
    yield
    rate_limit.reset()
