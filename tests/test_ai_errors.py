import logging

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.services.llm_service import AIServiceError


def test_ai_service_error_returns_500_and_hides_detail(
    monkeypatch, auth_headers, caplog
):
    def fail(text):
        raise AIServiceError("GEMINI_API_KEY is missing.")

    monkeypatch.setattr(main_module, "analyze_document", fail)
    client = TestClient(app)

    with caplog.at_level(logging.ERROR, logger="documind"):
        response = client.post(
            "/analyze",
            headers=auth_headers,
            files={"file": ("a.txt", b"Some invoice text.", "text/plain")}
        )

    assert response.status_code == 500
    assert "GEMINI_API_KEY" not in response.text
    assert any(
        record.exc_info and "GEMINI_API_KEY" in str(record.exc_info[1])
        for record in caplog.records
    )
