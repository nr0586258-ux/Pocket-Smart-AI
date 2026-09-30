"""Shared Jinja2 environment with a few helpers."""
import re

from fastapi.templating import Jinja2Templates

import config

templates = Jinja2Templates(directory=str(config.BASE_DIR / "templates"))


def inr(value) -> str:
    """Format a number as Indian rupees, e.g. 1234567 -> Rs 12,34,567."""
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return "₹0"
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        s = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head) + "," + tail
    return ("-" if n < 0 else "") + "₹" + s


templates.env.filters["inr"] = inr
templates.env.filters["when"] = lambda v: str(v)[:16].replace("T", " ")
templates.env.globals["CATEGORY_LABELS"] = {
    "home": "Home interior", "party": "Party", "jewelry": "Jewelry"}
