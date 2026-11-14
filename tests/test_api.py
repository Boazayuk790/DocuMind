from fastapi.testclient import TestClient

from app.main import app
from app.schemas import DocumentAnalysis
from app.database import initialize_database, save_analysis


client = TestClient(app)


def test_home_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_successful_document_analysis(monkeypatch):

    initialize_database()

    def mock_analyze(text):
        return DocumentAnalysis(
            document_type="Invoice",
            summary="Test invoice",
            key_information=["Invoice number: INV-001"],
            important_dates=[],
            amounts=["NGN 50,000"],
            missing_information=[],
            inconsistencies=[]
        )

    monkeypatch.setattr(
        "app.main.analyze_document",
        mock_analyze
    )

    response = client.post(
        "/analyze",
        files={
            "file": (
                "test.txt",
                b"This is a test invoice.",
                "text/plain"
            )
        }
    )

    assert response.status_code == 200
    assert response.json()["document_type"] == "Invoice"


def test_unsupported_file():
    response = client.post(
        "/analyze",
        files={
            "file": (
                "test.xlsx",
                b"test content",
                "application/octet-stream"
            )
        }
    )

    assert response.status_code == 400


def test_empty_file():
    response = client.post(
        "/analyze",
        files={
            "file": (
                "empty.txt",
                b"",
                "text/plain"
            )
        }
    )

    assert response.status_code == 400


def test_oversized_file():
    large_content = b"A" * (10 * 1024 * 1024 + 1)

    response = client.post(
        "/analyze",
        files={
            "file": (
                "large.txt",
                large_content,
                "text/plain"
            )
        }
    )

    assert response.status_code == 413




def test_analysis_not_found():
    response = client.get("/history/999999")

    assert response.status_code == 404



def test_delete_analysis():
    initialize_database()

    analysis = DocumentAnalysis(
        document_type="Invoice",
        summary="Deletion test",
        key_information=[],
        important_dates=[],
        amounts=[],
        missing_information=[],
        inconsistencies=[]
    )

    analysis_id = save_analysis("delete_test.txt", analysis)

    delete_response = client.delete(f"/history/{analysis_id}")

    assert delete_response.status_code == 200

    get_response = client.get(f"/history/{analysis_id}")

    assert get_response.status_code == 404


def test_chat_returns_answer(monkeypatch):
    initialize_database()

    analysis = DocumentAnalysis(
        document_type="Invoice", summary="Chat test"
    )
    analysis_id = save_analysis("chat_test.txt", analysis, "Total due: 500.")

    monkeypatch.setattr(
        "app.main.answer_question",
        lambda text, question: "The total due is 500."
    )

    response = client.post(
        "/chat",
        json={"analysis_id": analysis_id, "question": "What is due?"}
    )

    client.delete(f"/history/{analysis_id}")

    assert response.status_code == 200
    assert response.json()["answer"] == "The total due is 500."


def test_chat_without_stored_text():
    initialize_database()

    analysis = DocumentAnalysis(
        document_type="Invoice", summary="Old record"
    )
    analysis_id = save_analysis("old_record.txt", analysis)

    response = client.post(
        "/chat",
        json={"analysis_id": analysis_id, "question": "Anything?"}
    )

    client.delete(f"/history/{analysis_id}")

    assert response.status_code == 409


def test_chat_analysis_not_found():
    response = client.post(
        "/chat",
        json={"analysis_id": 999999, "question": "Anything?"}
    )

    assert response.status_code == 404


def test_compare_returns_result(monkeypatch):
    from app.schemas import DocumentComparison

    monkeypatch.setattr(
        "app.main.compare_documents",
        lambda a, b: DocumentComparison(
            summary="Test comparison",
            conflicting_amounts=["A: 500, B: 700"]
        )
    )

    response = client.post(
        "/compare",
        files={
            "file_a": ("a.txt", b"Total: 500", "text/plain"),
            "file_b": ("b.txt", b"Total: 700", "text/plain"),
        }
    )

    assert response.status_code == 200
    assert response.json()["conflicting_amounts"] == ["A: 500, B: 700"]


def test_compare_rejects_unsupported_file():
    response = client.post(
        "/compare",
        files={
            "file_a": ("a.txt", b"Total: 500", "text/plain"),
            "file_b": ("b.xlsx", b"data", "application/octet-stream"),
        }
    )

    assert response.status_code == 400
