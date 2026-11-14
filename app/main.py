from pathlib import Path
from uuid import uuid4
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel, Field

from app.services.document_reader import extract_text
from app.services.llm_service import analyze_document, answer_question, compare_documents
from app.schemas import DocumentAnalysis, DocumentComparison
from app.auth import create_token, get_current_user
from app.database import (
    initialize_database,
    save_analysis,
    get_analysis_history,
    get_analysis_by_id,
    delete_analysis,
    get_document_text,
    register_user,
    verify_user,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(lifespan=lifespan,
    title="DocuMind API",
    description="AI-powered document intelligence system",
    version="1.0.0"
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024


@app.get("/")
def home():
    return {
        "message": "Welcome to DocuMind API",
        "status": "running"
    }


@app.post("/analyze", response_model=DocumentAnalysis)
async def analyze_uploaded_document(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user)
):

    original_filename = file.filename or "unknown"
    extension = Path(original_filename).suffix.lower()

    if extension not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX and TXT files are supported."
        )

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Empty file.")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 10MB limit."
        )

    file_path = UPLOAD_DIR / f"{uuid4().hex}{extension}"

    try:
        file_path.write_bytes(content)

        document_text = extract_text(str(file_path))
        result = analyze_document(document_text)

        save_analysis(user_id, original_filename, result, document_text)

        return result

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Document analysis failed. Please try again."
        )

    finally:
        file_path.unlink(missing_ok=True)


@app.get("/history")
def document_history(user_id: int = Depends(get_current_user)):
    return get_analysis_history(user_id)


@app.get("/history/{analysis_id}")
def get_single_analysis(
    analysis_id: int,
    user_id: int = Depends(get_current_user)
):
    result = get_analysis_by_id(analysis_id, user_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found."
        )

    return result


@app.delete("/history/{analysis_id}")
def remove_analysis(
    analysis_id: int,
    user_id: int = Depends(get_current_user)
):
    deleted = delete_analysis(analysis_id, user_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found."
        )

    return {"message": "Analysis deleted successfully."}


class ChatRequest(BaseModel):
    analysis_id: int
    question: str = Field(min_length=1, max_length=1000)


@app.post("/chat")
def chat_with_document(
    request: ChatRequest,
    user_id: int = Depends(get_current_user)
):
    record = get_analysis_by_id(request.analysis_id, user_id)

    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    document_text = get_document_text(request.analysis_id, user_id)

    if not document_text:
        raise HTTPException(
            status_code=409,
            detail="No stored text for this analysis. Please upload and analyse the document again to chat with it."
        )

    try:
        answer = answer_question(document_text, request.question)
        return {"answer": answer}

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not answer the question. Please try again."
        )


async def read_and_extract(file: UploadFile) -> str:
    filename = file.filename or "unknown"
    extension = Path(filename).suffix.lower()

    if extension not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(
            status_code=400,
            detail=f"{filename}: only PDF, DOCX and TXT files are supported."
        )

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail=f"{filename}: empty file.")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"{filename}: file exceeds the 10MB limit."
        )

    file_path = UPLOAD_DIR / f"{uuid4().hex}{extension}"

    try:
        file_path.write_bytes(content)
        return extract_text(str(file_path))

    except ValueError as error:
        raise HTTPException(status_code=400, detail=f"{filename}: {error}")

    finally:
        file_path.unlink(missing_ok=True)


@app.post("/compare", response_model=DocumentComparison)
async def compare_uploaded_documents(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    user_id: int = Depends(get_current_user)
):
    text_a = await read_and_extract(file_a)
    text_b = await read_and_extract(file_b)

    try:
        return compare_documents(text_a, text_b)

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Document comparison failed. Please try again."
        )


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


@app.post("/register")
def register(credentials: Credentials):
    user_id = register_user(credentials.username, credentials.password)

    if user_id is None:
        raise HTTPException(
            status_code=409,
            detail="Username is already taken."
        )

    return {"token": create_token(user_id)}


@app.post("/login")
def login(credentials: Credentials):
    user_id = verify_user(credentials.username, credentials.password)

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password."
        )

    return {"token": create_token(user_id)}
