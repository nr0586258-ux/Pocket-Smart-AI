"""Deterministic recommendations used when Gemini is unavailable or returns
something unusable (no key, quota, bad JSON, over budget). Keeps the app useful."""
from services.catalog import match_home_item

PARTY_WEIGHTS = {
    "default": {"Catering": 0.45, "Decoration": 0.20, "Entertainment": 0.15, "Venue & Stay": 0.20},
    "birthday": {"Catering": 0.40, "Decoration": 0.25, "Entertainment": 0.20, "Venue & Stay": 0.15},
    "wedding": {"Catering": 0.40, "Decoration": 0.25, "Entertainment": 0.15, "Venue & Stay": 0.20},
    "corporate": {"Catering": 0.45, "Decoration": 0.15, "Entertainment": 0.10, "Venue & Stay": 0.30},
}


def home(req) -> dict:
    raw = []
    for it in req.items:
        name, platform, base = match_home_item(it.item)
        raw.append((it, name, platform, base))
    total = sum(base * it.quantity for it, _, _, base in raw)
    factor = min(req.budget / total, 1.5) if total else 1.0
    items = [
        {
            "name": f"{name} ({req.style.title()} style)",
            "category": it.room,
            "platform": platform,
            "price": int(base * factor),
            "quantity": it.quantity,
            "why": f"Balanced pick for the {it.room.lower()} that fits your budget.",
            "alternative": False,
        }
        for it, name, platform, base in raw
    ]
    return {
        "summary": (
            f"A {req.style} set-up across {len({i.room for i in req.items})} room(s), "
            "scaled to stay within your budget."
        ),
        "items": items,
        "tips": [
            "Buy bulkier items (sofa, bed) during IKEA or Amazon sale weeks.",
            "Prioritise fans and lights first; decor can be added later.",
        ],
    }


def party(req) -> dict:
    weights = dict(PARTY_WEIGHTS.get(req.event_type.lower(), PARTY_WEIGHTS["default"]))
    if not req.needs_stay:
        weights.pop("Venue & Stay")
    scale = sum(weights.values())
    ev = req.event_type.title()
    per_plate = int(req.budget * weights["Catering"] / scale * 0.95 / req.guests)
    options = {
        "Catering": (
            (f"{ev} catering buffet for {req.guests} guests (~Rs {per_plate}/plate)", "Zomato"),
            ("Bulk party menu order", "Swiggy"),
        ),
        "Decoration": ((f"{ev} theme decoration kit", "Amazon"), ("Balloon and backdrop combo", "Flipkart")),
        "Entertainment": (("Karaoke and party games kit", "Amazon"), ("Speaker and party lights bundle", "Flipkart")),
        "Venue & Stay": (("Guest rooms near the venue", "OYO"), ("Budget hotel block booking", "OYO")),
    }
    items = []
    for cat, weight in weights.items():
        share = req.budget * weight / scale
        (n1, p1), (n2, p2) = options[cat]
        items.append({"name": n1, "category": cat, "platform": p1, "price": int(share * 0.95),
                      "quantity": 1, "why": f"Main pick for {cat.lower()} at ~{round(weight / scale * 100)}% of budget.",
                      "alternative": False})
        items.append({"name": n2, "category": cat, "platform": p2, "price": int(share * 0.80),
                      "quantity": 1, "why": "A cheaper alternative if you want to save more.",
                      "alternative": True})
    return {
        "summary": f"A {ev.lower()} plan for {req.guests} guests with the budget split by category.",
        "items": items,
        "tips": ["Book catering and venue 2-3 weeks ahead for better rates.",
                 "Keep 5-10% of the budget aside for last-minute extras."],
    }


def jewelry(req) -> dict:
    parts = [("Necklace", 0.40, "Amazon"), ("Earrings", 0.25, "Flipkart"),
             ("Bangles / Bracelet", 0.25, "Amazon"), ("Ring", 0.10, "Flipkart")]
    metal = "" if req.metal.lower() in ("", "any") else f"{req.metal.title()} "
    items = [
        {"name": f"{req.style.title()} {metal}{part}", "category": "Jewelry set", "platform": platform,
         "price": int(req.budget * w * 0.95), "quantity": 1,
         "why": f"Suits a {req.occasion.lower()} look and the {req.style.lower()} style.",
         "alternative": False}
        for part, w, platform in parts
    ]
    return {
        "summary": f"A matching {req.style.lower()} set for {req.occasion.lower()}, kept within your budget.",
        "items": items,
        "tips": ["Choose one statement piece and keep the rest simple.",
                 "Check return policy and hallmark certification before buying."],
    }
