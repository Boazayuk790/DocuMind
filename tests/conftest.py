import pytest

import app.database as database


@pytest.fixture(autouse=True)
def temporary_database(tmp_path, monkeypatch):
    monkeypatch.setattr(
        database, "DATABASE_PATH", tmp_path / "test_documind.db"
    )
    database.initialize_database()
