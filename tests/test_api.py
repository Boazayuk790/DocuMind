from fastapi.testclient import TestClient

from app.main import app
from app.auth import create_token
from app.schemas import DocumentAnalysis, DocumentComparison
from app.database import save_analysis, register_user


client = TestClient(app)


def make_analysis(summary="Test"):
    return DocumentAnalysis(document_type="Invoice", summary=summary)


def test_home_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_successful_document_analysis(monkeypatch, auth_headers):
    monkeypatch.setattr(
        "app.main.analyze_document",
        lambda text: DocumentAnalysis(
            document_type="Invoice",
            summary="Test invoice",
            key_information=["Invoice number: INV-001"],
            amounts=["NGN 50,000"]
        )
    )

    response = client.post(
        "/analyze",
        headers=auth_headers,
        files={"file": ("test.txt", b"This is a test invoice.", "text/plain")}
    )

    assert response.status_code == 200
    assert response.json()["document_type"] == "Invoice"

    history = client.get("/history", headers=auth_headers).json()
    assert len(history) == 1


def test_unsupported_file(auth_headers):
    response = client.post(
        "/analyze",
        headers=auth_headers,
        files={"file": ("test.xlsx", b"test content", "application/octet-stream")}
    )

    assert response.status_code == 400


def test_empty_file(auth_headers):
    response = client.post(
        "/analyze",
        headers=auth_headers,
        files={"file": ("empty.txt", b"", "text/plain")}
    )

    assert response.status_code == 400


def test_oversized_file(auth_headers):
    large_content = b"A" * (10 * 1024 * 1024 + 1)

    response = client.post(
        "/analyze",
        headers=auth_headers,
        files={"file": ("large.txt", large_content, "text/plain")}
    )

    assert response.status_code == 413


def test_analysis_not_found(auth_headers):
    response = client.get("/history/999999", headers=auth_headers)

    assert response.status_code == 404


def test_delete_analysis(auth_headers, user_id):
    analysis_id = save_analysis(user_id, "delete_test.txt", make_analysis())

    delete_response = client.delete(
        f"/history/{analysis_id}", headers=auth_headers
    )
    assert delete_response.status_code == 200

    get_response = client.get(f"/history/{analysis_id}", headers=auth_headers)
    assert get_response.status_code == 404


def test_chat_returns_answer(monkeypatch, auth_headers, user_id):
    analysis_id = save_analysis(
        user_id, "chat_test.txt", make_analysis(), "Total due: 500."
    )

    monkeypatch.setattr(
        "app.main.answer_question",
        lambda text, question: "The total due is 500."
    )

    response = client.post(
        "/chat",
        headers=auth_headers,
        json={"analysis_id": analysis_id, "question": "What is due?"}
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "The total due is 500."


def test_chat_without_stored_text(auth_headers, user_id):
    analysis_id = save_analysis(user_id, "old_record.txt", make_analysis())

    response = client.post(
        "/chat",
        headers=auth_headers,
        json={"analysis_id": analysis_id, "question": "Anything?"}
    )

    assert response.status_code == 409


def test_chat_analysis_not_found(auth_headers):
    response = client.post(
        "/chat",
        headers=auth_headers,
        json={"analysis_id": 999999, "question": "Anything?"}
    )

    assert response.status_code == 404


def test_compare_returns_result(monkeypatch, auth_headers):
    monkeypatch.setattr(
        "app.main.compare_documents",
        lambda a, b: DocumentComparison(
            summary="Test comparison",
            conflicting_amounts=["A: 500, B: 700"]
        )
    )

    response = client.post(
        "/compare",
        headers=auth_headers,
        files={
            "file_a": ("a.txt", b"Total: 500", "text/plain"),
            "file_b": ("b.txt", b"Total: 700", "text/plain"),
        }
    )

    assert response.status_code == 200
    assert response.json()["conflicting_amounts"] == ["A: 500, B: 700"]


def test_compare_rejects_unsupported_file(auth_headers):
    response = client.post(
        "/compare",
        headers=auth_headers,
        files={
            "file_a": ("a.txt", b"Total: 500", "text/plain"),
            "file_b": ("b.xlsx", b"data", "application/octet-stream"),
        }
    )

    assert response.status_code == 400


def test_endpoints_require_token():
    text_file = {"file": ("a.txt", b"hello", "text/plain")}
    two_files = {
        "file_a": ("a.txt", b"hello", "text/plain"),
        "file_b": ("b.txt", b"hello", "text/plain"),
    }

    responses = [
        client.get("/history"),
        client.get("/history/1"),
        client.delete("/history/1"),
        client.post("/analyze", files=text_file),
        client.post("/compare", files=two_files),
        client.post("/chat", json={"analysis_id": 1, "question": "Hi?"}),
        client.get("/history", headers={"Authorization": "Bearer fake-token"}),
    ]

    assert all(r.status_code == 401 for r in responses)


def test_users_cannot_access_each_others_records(auth_headers, user_id):
    analysis_id = save_analysis(
        user_id, "private.txt", make_analysis(), "Secret text."
    )

    other_id = register_user("intruder", "intruder-password-1")
    other_headers = {"Authorization": f"Bearer {create_token(other_id)}"}

    assert client.get("/history", headers=other_headers).json() == []
    assert client.get(
        f"/history/{analysis_id}", headers=other_headers
    ).status_code == 404
    assert client.post(
        "/chat",
        headers=other_headers,
        json={"analysis_id": analysis_id, "question": "What?"}
    ).status_code == 404
    assert client.delete(
        f"/history/{analysis_id}", headers=other_headers
    ).status_code == 404

    assert client.get(
        f"/history/{analysis_id}", headers=auth_headers
    ).status_code == 200
