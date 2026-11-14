import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.document_reader import validate_content


def make_zip(names):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, "<x/>")
    return buffer.getvalue()


def test_valid_pdf_header_accepted():
    validate_content(".pdf", b"%PDF-1.7 rest of file")


def test_fake_pdf_rejected():
    with pytest.raises(ValueError):
        validate_content(".pdf", b"just text, not a pdf")


def test_valid_docx_structure_accepted():
    validate_content(".docx", make_zip(["word/document.xml"]))


def test_non_zip_docx_rejected():
    with pytest.raises(ValueError):
        validate_content(".docx", b"not a zip file")


def test_zip_without_document_xml_rejected():
    with pytest.raises(ValueError):
        validate_content(".docx", make_zip(["other.xml"]))


def test_txt_with_null_bytes_rejected():
    with pytest.raises(ValueError):
        validate_content(".txt", b"hello\x00world")


def test_txt_invalid_utf8_rejected():
    with pytest.raises(ValueError):
        validate_content(".txt", b"\xff\xfe\xfa bad bytes")


def test_analyze_rejects_fake_pdf(auth_headers):
    client = TestClient(app)
    response = client.post(
        "/analyze",
        headers=auth_headers,
        files={"file": ("fake.pdf", b"just text, not a pdf", "application/pdf")}
    )

    assert response.status_code == 400


def test_compare_rejects_fake_docx(auth_headers):
    client = TestClient(app)
    response = client.post(
        "/compare",
        headers=auth_headers,
        files={
            "file_a": ("a.txt", b"Valid text document.", "text/plain"),
            "file_b": ("b.docx", b"not a zip", "application/octet-stream")
        }
    )

    assert response.status_code == 400
