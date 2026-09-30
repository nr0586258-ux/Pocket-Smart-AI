"""Milestone 1 check: confirm your Gemini key works for text and image+text.

Usage (from project root, venv active):
    python scripts/test_gemini.py                # text only
    python scripts/test_gemini.py path/to/outfit.jpg   # text + image
"""
import mimetypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

if not config.GEMINI_API_KEY:
    sys.exit("GEMINI_API_KEY is missing. Copy .env.example to .env and add your key.")

from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

client = genai.Client(api_key=config.GEMINI_API_KEY)
print(f"Model: {config.GEMINI_MODEL}\n")

r = client.models.generate_content(
    model=config.GEMINI_MODEL,
    contents="In one sentence, suggest how to split a 20,000 rupee budget for a small birthday party.")
print("TEXT OK:", r.text.strip(), "\n")

if len(sys.argv) > 1:
    path = Path(sys.argv[1])
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    r = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=[types.Part.from_bytes(data=path.read_bytes(), mime_type=mime),
                  "Describe the colours in this outfit and suggest a matching jewelry metal."])
    print("IMAGE OK:", r.text.strip())
