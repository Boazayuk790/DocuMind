import pytest
from app.services.document_reader import extract_text


def test_extract_text_from_txt():
    text = extract_text("sample.txt")
    assert "DocuMind" in text


def test_missing_file():
    with pytest.raises(FileNotFoundError):
        extract_text("missing.txt")


def test_unsupported_file():
    with pytest.raises(ValueError):
        extract_text("sample.xlsx")