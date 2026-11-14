import os

from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

load_dotenv()

TOKEN_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


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
