"""Platform catalogue: search-link builders and mock product data.

Live scraping of Amazon/Flipkart/IKEA/Swiggy/Zomato/OYO is against their terms
and brittle, so PocketSmart builds *search links* to each platform and uses
AI-estimated prices. Mock data below powers the fallback recommendations.
"""
from urllib.parse import quote_plus

PLATFORM_URLS = {
    "Amazon": "https://www.amazon.in/s?k={q}",
    "Flipkart": "https://www.flipkart.com/search?q={q}",
    "IKEA": "https://www.ikea.com/in/en/search/?q={q}",
    "Swiggy": "https://www.swiggy.com/search?query={q}",
    "Zomato": "https://www.zomato.com/search?q={q}",
    "OYO": "https://www.oyorooms.com/search?location={q}",
}

ALLOWED_PLATFORMS = {
    "home": ["IKEA", "Amazon", "Flipkart"],
    "party": ["Swiggy", "Zomato", "OYO", "Amazon", "Flipkart"],
    "jewelry": ["Amazon", "Flipkart"],
}


def platform_url(platform: str, query: str) -> str:
    template = PLATFORM_URLS.get(platform)
    if template is None:
        return "https://www.google.com/search?q=" + quote_plus(f"{query} {platform}")
    return template.format(q=quote_plus(query))


# (product name, platform, typical unit price in INR)
HOME_CATALOG = {
    "light": ("LED Ceiling Light", "Amazon", 1200),
    "lamp": ("Table Lamp", "IKEA", 1500),
    "ceiling fan": ("BLDC Ceiling Fan 1200mm", "Amazon", 3800),
    "fan": ("BLDC Ceiling Fan 1200mm", "Amazon", 3800),
    "dining table": ("4-Seater Dining Table", "IKEA", 14000),
    "sofa": ("3-Seater Fabric Sofa", "IKEA", 22000),
    "bed": ("Queen Size Bed Frame", "IKEA", 16000),
    "mattress": ("Queen Orthopaedic Mattress", "Amazon", 11000),
    "wardrobe": ("2-Door Wardrobe", "IKEA", 18000),
    "curtain": ("Blackout Curtains (Pair)", "Amazon", 1800),
    "rug": ("Woven Area Rug", "IKEA", 3500),
    "wall art": ("Framed Wall Art Set", "Flipkart", 1500),
    "study table": ("Study Desk", "Flipkart", 6000),
    "tv unit": ("TV Unit with Storage", "Flipkart", 9000),
    "coffee table": ("Coffee Table", "IKEA", 5000),
    "bookshelf": ("5-Tier Bookshelf", "Amazon", 4500),
    "chair": ("Ergonomic Chair", "Amazon", 5500),
}
HOME_DEFAULT = ("Home Decor Piece", "Amazon", 2000)


def match_home_item(name: str):
    n = name.lower().strip()
    for key, value in HOME_CATALOG.items():
        if key in n or n in key:
            return value
    return HOME_DEFAULT
