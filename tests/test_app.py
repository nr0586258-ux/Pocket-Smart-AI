"""End-to-end tests. Gemini is never called: the key is blank (fallback path)
or call_gemini is monkeypatched."""
import pytest
from fastapi.testclient import TestClient

import config
from services import gemini_utils


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    gemini_utils._client.cache_clear()
    from main import app
    with TestClient(app) as c:
        yield c


def register(client, name="tester"):
    return client.post("/register", data={"username": name, "email": "t@example.com",
                                          "password": "secret123", "confirm": "secret123"},
                       follow_redirects=False)


HOME = {"budget": 60000, "style": "modern", "notes": "",
        "items": [{"room": "Living Room", "item": "Lights", "quantity": 3},
                  {"room": "Kitchen", "item": "Ceiling fan", "quantity": 2},
                  {"room": "Dining Room", "item": "Dining table", "quantity": 1}]}


def test_pages_public(client):
    assert client.get("/").status_code == 200
    assert client.get("/testimonials").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/health").json()["status"] == "ok"


def test_protected_pages_redirect(client):
    r = client.get("/dashboard", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert client.post("/generate-home", json=HOME).status_code == 401


def test_register_login_logout_token(client):
    assert register(client).status_code == 303
    assert client.get("/dashboard").status_code == 200
    assert client.get("/session-info").json()["logged_in"] is True
    client.get("/logout")
    assert client.get("/session-info").json()["logged_in"] is False
    bad = client.post("/login", data={"username": "tester", "password": "nope"})
    assert bad.status_code == 400
    ok = client.post("/login", data={"username": "TESTER", "password": "secret123"},
                     follow_redirects=False)
    assert ok.status_code == 303
    tok = client.post("/token", data={"username": "tester", "password": "secret123"}).json()
    assert tok["token_type"] == "bearer"


def test_duplicate_and_invalid_registration(client):
    register(client)
    assert register(client).status_code == 400
    r = client.post("/register", data={"username": "x", "email": "bad", "password": "1",
                                       "confirm": "2"})
    assert r.status_code == 400


def test_home_fallback_within_budget_and_history(client):
    register(client)
    r = client.post("/generate-home", json=HOME)
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "fallback" and data["within_budget"] is True
    assert data["total_estimated"] <= HOME["budget"]
    assert all(i["url"].startswith("https://") for i in data["items"])
    page = client.get(f"/recommendations/{data['history_id']}")
    assert page.status_code == 200 and "Living Room" in page.text
    assert client.get("/history").status_code == 200
    assert len(client.get("/api/history").json()["items"]) == 1
    assert client.get("/recommendations-details", params={"category": "home"}).status_code == 200
    assert client.get("/session-data").json()["plans_this_session"] == 1


def test_party_and_stay(client):
    register(client)
    body = {"budget": 50000, "guests": 40, "event_type": "Birthday", "needs_stay": True}
    data = client.post("/generate-party", json=body).json()
    cats = {a["category"] for a in data["allocation"]}
    assert {"Catering", "Decoration", "Entertainment", "Venue & Stay"} <= cats
    assert data["within_budget"]
    body["needs_stay"] = False
    cats = {a["category"] for a in client.post("/generate-party", json=body).json()["allocation"]}
    assert "Venue & Stay" not in cats


def test_jewelry_with_and_without_image(client):
    register(client)
    form = {"budget": "20000", "occasion": "Wedding", "style": "Classic", "metal": "Gold"}
    assert client.post("/generate-jewelry", data=form).status_code == 200
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 50
    r = client.post("/generate-jewelry", data=form, files={"outfit_image": ("o.png", png, "image/png")})
    assert r.status_code == 200 and r.json()["total_estimated"] <= 20000
    bad = client.post("/generate-jewelry", data=form, files={"outfit_image": ("o.txt", b"hi", "text/plain")})
    assert bad.status_code == 415


def test_validation_errors(client):
    register(client)
    assert client.post("/generate-home", json={**HOME, "budget": -5}).status_code == 422
    assert client.post("/generate-home", json={**HOME, "items": []}).status_code == 422
    assert client.post("/generate-party", json={"budget": 100, "guests": 0, "event_type": "x"}).status_code == 422
    assert client.post("/generate-jewelry", data={"budget": "0", "occasion": "x"}).status_code == 422


def test_gemini_result_used_and_over_budget_falls_back(client, monkeypatch):
    register(client)
    good = {"summary": "ok", "tips": ["t"], "items": [
        {"name": "Fan", "category": "Kitchen", "platform": "amazon", "price": 3000, "quantity": 2}]}
    monkeypatch.setattr(gemini_utils, "call_gemini", lambda p, image=None: good)
    data = client.post("/generate-home", json=HOME).json()
    assert data["source"] == "gemini" and data["items"][0]["platform"] == "Amazon"

    pricey = {"summary": "x", "items": [
        {"name": "Gold fan", "category": "Kitchen", "platform": "IKEA", "price": 900000, "quantity": 1}]}
    monkeypatch.setattr(gemini_utils, "call_gemini", lambda p, image=None: pricey)
    data = client.post("/generate-home", json=HOME).json()
    assert data["source"] == "fallback" and data["within_budget"]


def test_users_cannot_see_each_others_history(client):
    register(client, "alice")
    hid = client.post("/generate-home", json=HOME).json()["history_id"]
    client.get("/logout")
    register(client, "bob")
    assert client.get(f"/recommendations/{hid}").status_code == 404
