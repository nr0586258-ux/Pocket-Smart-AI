"""Register, login, logout, token and session endpoints."""
import re
import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

import config
import database
from models.schemas import Token
from services import auth
from templating import templates

router = APIRouter()

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _login_redirect(user: dict) -> RedirectResponse:
    resp = RedirectResponse("/dashboard", status_code=303)
    resp.set_cookie(auth.COOKIE_NAME, auth.create_access_token(user), httponly=True,
                    samesite="lax", max_age=config.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return resp


@router.get("/login")
def login_page(request: Request):
    if auth.get_optional_user(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"user": None, "error": None})


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = auth.authenticate(username, password)
    if not user:
        return templates.TemplateResponse(
            request, "login.html",
            {"user": None, "error": "Username or password is incorrect.", "username": username},
            status_code=400)
    request.session.clear()
    request.session["user_id"] = user["id"]
    return _login_redirect(user)


@router.get("/register")
def register_page(request: Request):
    if auth.get_optional_user(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(request, "register.html", {"user": None, "error": None})


@router.post("/register")
def register(request: Request, username: str = Form(...), email: str = Form(...),
             password: str = Form(...), confirm: str = Form(...)):
    username, email = username.strip(), email.strip()
    error = None
    if not USERNAME_RE.match(username):
        error = "Username must be 3-30 characters: letters, numbers, dot, dash or underscore."
    elif not EMAIL_RE.match(email):
        error = "Enter a valid email address."
    elif not 6 <= len(password.encode()) <= 72:
        error = "Password must be 6-72 characters."
    elif password != confirm:
        error = "Passwords do not match."
    user = None
    if not error:
        try:
            uid = database.create_user(username, email, auth.hash_password(password))
            user = database.get_user_by_id(uid)
        except sqlite3.IntegrityError:
            error = "That username is taken. Try another one."
    if error:
        return templates.TemplateResponse(
            request, "register.html",
            {"user": None, "error": error, "username": username, "email": email}, status_code=400)
    request.session.clear()
    request.session["user_id"] = user["id"]
    return _login_redirect(user)


@router.api_route("/logout", methods=["GET", "POST"])
def logout(request: Request):
    request.session.clear()
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(auth.COOKIE_NAME)
    return resp


@router.post("/token", response_model=Token)
def token(form: OAuth2PasswordRequestForm = Depends()):
    user = auth.authenticate(form.username, form.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"})
    return Token(access_token=auth.create_access_token(user))


@router.get("/session-info")
def session_info(request: Request):
    user = auth.get_optional_user(request)
    return {"logged_in": bool(user), "user_id": user["id"] if user else None,
            "username": user["username"] if user else None}


@router.get("/session-data")
def session_data(request: Request, user: dict = Depends(auth.get_current_user_api)):
    return {
        "user_id": user["id"],
        "username": user["username"],
        "last_category": request.session.get("last_category"),
        "plans_this_session": request.session.get("plans_this_session", 0),
        "plans_by_category": database.count_history_by_category(user["id"]),
    }
