"""AI planner endpoints plus history / details APIs."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import ValidationError

import config
import database
from models.schemas import HomeRequest, JewelryRequest, PartyRequest
from services import auth, gemini_utils

router = APIRouter()


def _record(request: Request, user: dict, category: str, req_data: dict, result: dict) -> dict:
    history_id = database.save_history(user["id"], category, req_data, result)
    request.session["last_category"] = category
    request.session["plans_this_session"] = request.session.get("plans_this_session", 0) + 1
    return {**result, "history_id": history_id}


@router.post("/generate-home")
def generate_home(req: HomeRequest, request: Request,
                  user: dict = Depends(auth.get_current_user_api)):
    result = gemini_utils.get_home_recommendations(req)
    return _record(request, user, "home", req.model_dump(), result)


@router.post("/generate-party")
def generate_party(req: PartyRequest, request: Request,
                   user: dict = Depends(auth.get_current_user_api)):
    result = gemini_utils.get_party_recommendations(req)
    return _record(request, user, "party", req.model_dump(), result)


@router.post("/generate-jewelry")
def generate_jewelry(
    request: Request,
    budget: float = Form(...),
    occasion: str = Form(...),
    style: str = Form("classic"),
    metal: str = Form("any"),
    notes: str = Form(""),
    outfit_image: UploadFile | None = File(None),
    user: dict = Depends(auth.get_current_user_api),
):
    try:
        req = JewelryRequest(budget=budget, occasion=occasion, style=style or "classic",
                             metal=metal or "any", notes=notes)
    except ValidationError as exc:
        first = exc.errors()[0]
        raise HTTPException(status_code=422, detail=f"{first['loc'][-1]}: {first['msg']}")

    image = None
    if outfit_image is not None and outfit_image.filename:
        if outfit_image.content_type not in config.ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=415, detail="Upload a JPG, PNG or WebP image.")
        data = outfit_image.file.read(config.MAX_IMAGE_BYTES + 1)
        if len(data) > config.MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Image is larger than 5 MB.")
        if data:
            image = (data, outfit_image.content_type)

    result = gemini_utils.get_jewelry_recommendations(req, image)
    req_data = {**req.model_dump(), "has_image": image is not None}
    return _record(request, user, "jewelry", req_data, result)


@router.get("/recommendations-details")
def recommendation_details(id: int | None = None, category: str | None = None,
                           user: dict = Depends(auth.get_current_user_api)):
    if id is not None:
        item = database.get_history_item(user["id"], id)
    else:
        rows = database.list_history(user["id"], limit=1, category=category)
        item = rows[0] if rows else None
    if not item:
        raise HTTPException(status_code=404, detail="No recommendation found.")
    return item


@router.get("/api/history")
def history_api(category: str | None = None, limit: int = 50,
                user: dict = Depends(auth.get_current_user_api)):
    return {"items": database.list_history(user["id"], min(max(limit, 1), 200), category)}
