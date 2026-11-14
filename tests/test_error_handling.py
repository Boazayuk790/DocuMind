import logging

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


def test_unexpected_error_is_logged_but_not_leaked(
    monkeypatch, auth_headers, caplog
):
    def explode(text):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(main_module, "analyze_document", explode)
    client = TestClient(app)

    with caplog.at_level(logging.ERROR, logger="documind"):
        response = client.post(
            "/analyze",
            headers=auth_headers,
            files={"file": ("a.txt", b"Some invoice text.", "text/plain")}
        )

    assert response.status_code == 500
    assert "secret internal detail" not in response.text
    assert any(
        record.exc_info and "secret internal detail" in str(record.exc_info[1])
        for record in caplog.records
    )
