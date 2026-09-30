"""Password hashing, JWT handling and FastAPI auth dependencies."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, Request

import config
import database

COOKIE_NAME = "access_token"
ALGORITHM = "HS256"


class NotAuthenticated(Exception):
    """Raised by page routes; main.py turns it into a redirect to /login."""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def authenticate(username: str, password: str):
    user = database.get_user_by_username(username.strip())
    if user and verify_password(password, user["password_hash"]):
        return user
    return None


def create_access_token(user: dict) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user["id"]), "username": user["username"], "exp": exp},
                      config.SECRET_KEY, algorithm=ALGORITHM)


def _token_from_request(request: Request):
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.cookies.get(COOKIE_NAME)


def get_optional_user(request: Request):
    token = _token_from_request(request)
    if not token:
        return None
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITHM])
        user = database.get_user_by_id(int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
    return user


def get_current_user_api(request: Request) -> dict:
    user = get_optional_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Please log in to continue.",
                            headers={"WWW-Authenticate": "Bearer"})
    return user


def get_current_user_page(request: Request) -> dict:
    user = get_optional_user(request)
    if not user:
        raise NotAuthenticated()
    return user
