"""Gemini integration: prompt building, API calls, validation and fallback."""
import json
import logging
import re
from functools import lru_cache

import config
from services import fallback
from services.catalog import ALLOWED_PLATFORMS, platform_url

log = logging.getLogger("pocketsmart.gemini")

SYSTEM_PROMPT = (
    "You are PocketSmart AI, a careful budget-planning assistant for Indian shoppers. "
    "All prices are in Indian Rupees (INR) and must be realistic. You never exceed the "
    "user's budget. You reply with valid JSON only, with no markdown and no commentary."
)

OUTPUT_SPEC = """
Return ONLY a JSON object in exactly this shape:
{
  "summary": "2-3 sentence overview of the plan",
  "items": [
    {"name": "specific product or service", "category": "string",
     "platform": "one of the allowed platforms", "price": 0,
     "quantity": 1, "why": "one short reason", "alternative": false}
  ],
  "tips": ["short money-saving tip"]
}
Rules: "price" is the INR price per unit (integer). The sum of price x quantity over items
where alternative is false MUST NOT exceed the budget. Items marked alternative=true are
cheaper substitutes and are not counted in the total. Use only the allowed platforms.
"""


@lru_cache(maxsize=1)
def _client():
    if not config.GEMINI_API_KEY:
        return None
    from google import genai

    return genai.Client(api_key=config.GEMINI_API_KEY)


def _parse_json(text: str):
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


def call_gemini(prompt: str, image: tuple[bytes, str] | None = None):
    """Send text (+ optional image) to Gemini. Returns a dict or None on any failure."""
    client = _client()
    if client is None:
        return None
    try:
        from google.genai import types

        contents = []
        if image:
            contents.append(types.Part.from_bytes(data=image[0], mime_type=image[1]))
        contents.append(prompt)
        resp = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.4,
            ),
        )
        return _parse_json(resp.text)
    except Exception as exc:  # network, quota, safety block, bad key...
        log.warning("Gemini call failed: %s", exc)
        return None


def _to_number(value, default=0.0) -> float:
    try:
        return max(float(str(value).replace(",", "").replace("₹", "")), 0.0)
    except (TypeError, ValueError):
        return default


def finalize(raw, category: str, budget: float, source: str):
    """Validate/normalise a raw result. Returns None if it is unusable."""
    if not isinstance(raw, dict) or not isinstance(raw.get("items"), list):
        return None
    allowed = ALLOWED_PLATFORMS[category]
    lookup = {p.lower(): p for p in allowed}
    items = []
    for it in raw["items"]:
        if not isinstance(it, dict) or not str(it.get("name", "")).strip():
            continue
        platform = lookup.get(str(it.get("platform", "")).strip().lower(), allowed[0])
        name = str(it["name"]).strip()[:140]
        try:
            qty = max(int(it.get("quantity", 1)), 1)
        except (TypeError, ValueError):
            qty = 1
        items.append({
            "name": name,
            "category": str(it.get("category") or "General").strip()[:60],
            "platform": platform,
            "price": round(_to_number(it.get("price"))),
            "quantity": qty,
            "why": str(it.get("why", "")).strip()[:240],
            "alternative": bool(it.get("alternative", False)),
            "url": platform_url(platform, name),  # built server-side, never trusted from the model
        })
    if not items or not any(not i["alternative"] for i in items):
        return None

    totals: dict[str, float] = {}
    for i in items:
        if not i["alternative"]:
            totals[i["category"]] = totals.get(i["category"], 0) + i["price"] * i["quantity"]
    total = sum(totals.values())
    allocation = [
        {"category": c, "amount": round(a), "percent": round(a / total * 100) if total else 0}
        for c, a in totals.items()
    ]
    tips = [str(t)[:200] for t in raw.get("tips", []) if str(t).strip()][:5]
    return {
        "category": category,
        "budget": round(budget),
        "summary": str(raw.get("summary", "")).strip()[:600],
        "allocation": allocation,
        "items": items,
        "tips": tips,
        "total_estimated": round(total),
        "within_budget": total <= budget * 1.05,
        "source": source,
        "disclaimer": "Prices are AI estimates. Check each platform for live prices and availability.",
    }


def _run(category, budget, prompt, fallback_raw, image=None):
    """Try Gemini (twice, second time with a budget correction), else fall back."""
    attempt_prompt = prompt
    for _ in range(2):
        result = finalize(call_gemini(attempt_prompt, image), category, budget, "gemini")
        if result and result["within_budget"]:
            return result
        if result is None:
            break  # no key / bad JSON: a second identical call will not help
        attempt_prompt = (
            prompt + f"\nYour previous plan cost INR {result['total_estimated']}, which exceeds "
            f"the budget of INR {round(budget)}. Produce a cheaper plan that fits."
        )
    return finalize(fallback_raw(), category, budget, "fallback")


# ---- public API used by the routes -------------------------------------------------

def get_home_recommendations(req):
    lines = "\n".join(f"- {i.room}: {i.quantity} x {i.item}" for i in req.items)
    prompt = (
        f"Plan a home interior shopping list.\nTotal budget: INR {req.budget:.0f}\n"
        f"Style: {req.style}\nNotes: {req.notes or 'none'}\nItems needed:\n{lines}\n"
        f"Allowed platforms: {', '.join(ALLOWED_PLATFORMS['home'])}.\n"
        "Every requested item and quantity must appear once. Use the room name as the category. "
        "Balance function, style and price." + OUTPUT_SPEC
    )
    return _run("home", req.budget, prompt, lambda: fallback.home(req))


def get_party_recommendations(req):
    stay = "Include an accommodation option (OYO) for guests." if req.needs_stay else \
        "Do not include accommodation."
    prompt = (
        f"Plan a {req.event_type} party.\nTotal budget: INR {req.budget:.0f}\nGuests: {req.guests}\n"
        f"Venue: {req.venue or 'not decided'}\nCity: {req.city or 'not specified'}\n"
        f"Notes: {req.notes or 'none'}\n"
        f"Split the budget across the categories Catering, Decoration and Entertainment"
        f"{' and Venue & Stay' if req.needs_stay else ''}, weighted for a {req.event_type}. "
        f"{stay} Give one main pick and one cheaper alternative per category "
        "(quantity 1, price is the total for that line). "
        f"Allowed platforms: {', '.join(ALLOWED_PLATFORMS['party'])}." + OUTPUT_SPEC
    )
    return _run("party", req.budget, prompt, lambda: fallback.party(req))


def get_jewelry_recommendations(req, image: tuple[bytes, str] | None = None):
    img_note = ("An image of the outfit is attached: match colours and neckline to it."
                if image else "No outfit image was provided.")
    prompt = (
        f"Recommend a matching jewelry set.\nTotal budget: INR {req.budget:.0f}\n"
        f"Occasion: {req.occasion}\nStyle: {req.style}\nPreferred metal: {req.metal}\n"
        f"Notes: {req.notes or 'none'}\n{img_note}\n"
        "Suggest 3-5 pieces (e.g. necklace, earrings, bangles, ring) that work together, "
        "category 'Jewelry set', and mention colour coordination in 'why'. "
        f"Allowed platforms: {', '.join(ALLOWED_PLATFORMS['jewelry'])}." + OUTPUT_SPEC
    )
    return _run("jewelry", req.budget, prompt, lambda: fallback.jewelry(req), image)
