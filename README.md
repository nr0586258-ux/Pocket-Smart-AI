# PocketSmart AI

Budget-first recommendations for Home interiors, Parties and Jewelry.
FastAPI + Jinja2 + SQLite + Google Gemini (text and image input).

## Setup (VS Code)
1. Install Python 3.10+ and VS Code (with the Python extension).
2. File > Open Folder > `pocketsmart-ai`. Open a terminal (Ctrl+`).
3. Create and activate a virtual environment:
   - Windows: `python -m venv .venv` then `.venv\Scripts\activate`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. Copy `.env.example` to `.env`, then set `GEMINI_API_KEY`
   (free key: https://aistudio.google.com/apikey) and a random `SECRET_KEY`.
6. Select the `.venv` interpreter: Ctrl+Shift+P > "Python: Select Interpreter".

## Run
`python main.py`  (or `uvicorn main:app --reload`) then open http://127.0.0.1:8000
Interactive API docs: http://127.0.0.1:8000/docs

## Test
- Gemini connectivity: `python scripts/test_gemini.py` (add an image path to test multimodal)
- Automated tests (no API key needed): `pytest -v`
- Manual: register, then try each planner. Without a key the app serves fallback plans.

## Notes
- The model is set by `GEMINI_MODEL` (default `gemini-2.5-flash`). Gemini 1.5 models are retired.
- Product links are search links to each platform and prices are AI estimates; no scraping.
