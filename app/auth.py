import os

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

load_dotenv()

TOKEN_MAX_AGE_SECONDS = 24 * 60 * 60

bearer_scheme = HTTPBearer(auto_error=False)


def _serializer():
    secret = os.getenv("SECRET_KEY")

    if not secret:
        raise ValueError("SECRET_KEY is missing.")

    return URLSafeTimedSerializer(secret, salt="documind-auth")


def create_token(user_id):
    return _serializer().dumps({"user_id": user_id})


def verify_token(token):
    try:
        data = _serializer().loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
        return data["user_id"]
    except (BadSignature, SignatureExpired, KeyError):
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = verify_token(credentials.credentials)

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user_id
