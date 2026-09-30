"""HTML pages rendered with Jinja2."""
from fastapi import APIRouter, Depends, HTTPException, Request

import database
from services import auth
from templating import templates

router = APIRouter()
page_user = Depends(auth.get_current_user_page)


def _render(request, name, user, **ctx):
    return templates.TemplateResponse(request, name, {"user": user, **ctx})


@router.get("/")
def index(request: Request):
    return _render(request, "index.html", auth.get_optional_user(request))


@router.get("/testimonials")
def testimonials(request: Request):
    return _render(request, "testimonials.html", auth.get_optional_user(request))


@router.get("/dashboard")
def dashboard(request: Request, user: dict = page_user):
    return _render(request, "dashboard.html", user,
                   recent=database.list_history(user["id"], limit=5),
                   counts=database.count_history_by_category(user["id"]))


@router.get("/home-planner")
def home_planner(request: Request, user: dict = page_user):
    return _render(request, "home_planner.html", user)


@router.get("/party-planner")
def party_planner(request: Request, user: dict = page_user):
    return _render(request, "party_planner.html", user)


@router.get("/jewelry-planner")
def jewelry_planner(request: Request, user: dict = page_user):
    return _render(request, "jewelry_planner.html", user)


@router.get("/recommendations/{item_id}")
def recommendation_page(item_id: int, request: Request, user: dict = page_user):
    item = database.get_history_item(user["id"], item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    return _render(request, "recommendations.html", user, item=item, data=item["response"],
                   category=item["category"])


@router.get("/history")
def history_page(request: Request, user: dict = page_user):
    return _render(request, "history.html", user, rows=database.list_history(user["id"], limit=100))


@router.get("/health")
def health():
    import config
    return {"status": "ok", "gemini_configured": bool(config.GEMINI_API_KEY),
            "model": config.GEMINI_MODEL}
