"""PocketSmart AI - FastAPI entry point.

Run:  python main.py      (or)      uvicorn main:app --reload
"""
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

import config
import database
from routes import auth_routes, pages, planner_routes
from services.auth import NotAuthenticated
from templating import templates

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pocketsmart")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # "startup": initialise DB and report configuration
    database.init_db()
    if not config.GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY is not set: the app will use fallback recommendations.")
    else:
        log.info("Gemini ready (model: %s)", config.GEMINI_MODEL)
    if config.SECRET_KEY == "dev-only-change-me":
        log.warning("SECRET_KEY is the default. Set a random value in .env before deploying.")
    yield


app = FastAPI(title="PocketSmart AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY, same_site="lax",
                   max_age=config.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

app.mount("/static", StaticFiles(directory=str(config.BASE_DIR / "static")), name="static")


@app.exception_handler(NotAuthenticated)
async def _not_authenticated(request: Request, exc: NotAuthenticated):
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(StarletteHTTPException)
async def _http_error(request: Request, exc: StarletteHTTPException):
    wants_html = "text/html" in request.headers.get("accept", "")
    if wants_html and exc.status_code in (404, 403):
        return templates.TemplateResponse(
            request, "error.html", {"user": None, "code": exc.status_code, "message": exc.detail},
            status_code=exc.status_code)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code,
                        headers=getattr(exc, "headers", None))


app.include_router(pages.router)
app.include_router(auth_routes.router)
app.include_router(planner_routes.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
