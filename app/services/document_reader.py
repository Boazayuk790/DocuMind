import io
import zipfile
from pathlib import Path
from pypdf import PdfReader
from docx import Document


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def extract_text(file_path: str) -> str:
    path = Path(file_path)

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported document format.")

    if not path.exists():
        raise FileNotFoundError("Document not found.")

    if extension == ".pdf":
        reader = PdfReader(str(path))
        text = "\n".join(
            page.extract_text() or "" for page in reader.pages
        )

    elif extension == ".docx":
        document = Document(str(path))
        text = "\n".join(
            paragraph.text for paragraph in document.paragraphs
        )

    else:
        text = path.read_text(encoding="utf-8")

    text = text.strip()

    if not text:
        raise ValueError("No readable text found in document.")

    return text


MAX_UNCOMPRESSED_DOCX_BYTES = 50 * 1024 * 1024


def validate_content(extension: str, content: bytes) -> None:
    if extension == ".pdf":
        if b"%PDF-" not in content[:1024]:
            raise ValueError("File content is not a valid PDF.")

    elif extension == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise ValueError("File content is not a valid DOCX.")
                total = sum(info.file_size for info in archive.infolist())
                if total > MAX_UNCOMPRESSED_DOCX_BYTES:
                    raise ValueError("DOCX file is too large when unpacked.")
        except zipfile.BadZipFile:
            raise ValueError("File content is not a valid DOCX.")

    elif extension == ".txt":
        if b"\x00" in content:
            raise ValueError("File content is not valid text.")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Text file must be UTF-8 encoded.")

    else:
        raise ValueError("Unsupported document format.")
