"""Store, storage and API checks on a throwaway SQLite database (no Supabase, no models, no network).
Run: python -m tests.test_store
"""

import asyncio
import hashlib
import hmac
import json
import sys
import tempfile
import time
import types
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Header
from fastapi.testclient import TestClient

import server.storage as storage
from server.gateway import api
from server.storage import LocalStore
from server.store import repo
from server.store.db import make_engine, sessions, use_engine
from server.store.models import Base, ContactMessage, Cv, InterviewSession, Profile

TMP = Path(tempfile.mkdtemp())


async def fresh_db(name: str):
    engine = make_engine(f"sqlite+aiosqlite:///{TMP / name}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    use_engine(engine)
    return engine


def new_session_fields(**over):
    return {"pack_id": "tech_behavioral", "role": "SWE", "seniority": "mid", "interview_type": "mixed"} | over


async def test_credits():
    engine = await fresh_db("credits.db")
    async with sessions()() as db:
        p = await repo.profile(db, "alice")
        assert p.credits == 2
        a = (await repo.create_session(db, "alice", **new_session_fields())).id  # ids only: a failed charge rolls back
        assert await repo.charge(db, "alice", a), "first charge starts it"
        assert not await repo.charge(db, "alice", a), "a session is paid once"
        assert not await repo.charge(db, "bob", a), "someone else can't start it"
        assert (await db.get(Profile, "alice", populate_existing=True)).credits == 1

        await repo.refund(db, a)
        await repo.refund(db, a)
        assert (await db.get(Profile, "alice", populate_existing=True)).credits == 2, "refunded exactly once"

        p = await db.get(Profile, "alice", populate_existing=True)
        p.credits = 0
        await db.commit()
        try:
            await repo.create_session(db, "alice", **new_session_fields())
        except repo.NoCredits:
            pass
        else:
            raise AssertionError("no credits: can't create")

        p.pass_until = datetime.now(UTC) + timedelta(days=1)
        await db.commit()
        b = (await repo.create_session(db, "alice", **new_session_fields())).id
        assert await repo.charge(db, "alice", b), "an active pass pays"
        assert not (await db.get(InterviewSession, b, populate_existing=True)).charged, "no credit taken on a pass"

        cv = await repo.add_cv(db, "alice", file_name="cv.pdf", raw_text="x", cv_profile={})
        assert await repo.get_cv(db, "bob", cv.id) is None and await repo.get_session(db, "bob", a) is None
        try:
            await repo.create_session(db, "bob", **new_session_fields(cv_id=cv.id))
        except ValueError:
            pass
        else:
            raise AssertionError("can't attach someone else's CV")
    await engine.dispose()
    print("credits + isolation PASS")


async def test_local_store():
    store = LocalStore(str(TMP / "blobs"), "secret", "http://gw")
    await store.put("cvs/u/a.txt", b"hello", "text/plain")
    assert await store.get("cvs/u/a.txt") == b"hello"
    url = await store.signed_url("cvs/u/a.txt", 60)
    exp, sig = int(url.split("exp=")[1].split("&")[0]), url.split("sig=")[1]
    assert store.verify("cvs/u/a.txt", exp, sig)
    assert not store.verify("cvs/u/b.txt", exp, sig), "signature is bound to the key"
    assert not store.verify("cvs/u/a.txt", int(time.time()) - 1, store._sig("cvs/u/a.txt", int(time.time()) - 1)), "expired"
    try:
        store.path("../../etc/passwd")
    except ValueError:
        pass
    else:
        raise AssertionError("keys can't escape the store")
    await store.delete("cvs/u/a.txt")
    assert not store.path("cvs/u/a.txt").exists()
    print("local storage PASS")


def test_api():
    asyncio.run(fresh_db("api.db"))
    storage._store = LocalStore(str(TMP / "api-blobs"), "secret", "http://testserver")
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api._user] = lambda authorization=Header(""): authorization.removeprefix("Bearer ") or "anon"
    client = TestClient(app).__enter__()  # one event loop for the whole test: recording anonymization runs in the background
    alice, bob = {"Authorization": "Bearer alice"}, {"Authorization": "Bearer bob"}

    def recording_settled(sid):
        for _ in range(100):
            detail = client.get(f"/sessions/{sid}", headers=alice).json()
            if detail["recording_status"] != "processing":
                return detail
            time.sleep(0.05)
        raise AssertionError("recording still processing")

    # stand-in for the voice converter (no models): marks what it was given; "boom" makes it fail
    def fake_anonymize(data):
        if data == b"boom":
            raise RuntimeError("conversion failed")
        return b"anon:" + data

    sys.modules["server.services.voice_anon"] = types.SimpleNamespace(anonymize_recording=fake_anonymize)

    assert client.get("/me", headers=alice).json() == {"credits": 2, "has_pass": False}
    async def add_cv(uid):
        async with sessions()() as db:
            return str((await repo.add_cv(db, uid, file_name="cv.txt", raw_text="x", cv_profile=None)).id)

    cv = asyncio.run(add_cv("alice"))
    body = {"pack_id": "tech_behavioral", "role": "SWE", "seniority": "mid", "interview_type": "mixed", "cv_id": cv}
    no_cv = {k: v for k, v in body.items() if k != "cv_id"}
    assert client.post("/sessions", json=no_cv, headers=alice).status_code == 422, "CV is required"
    assert client.post("/sessions", json=body, headers=bob).status_code == 422, "can't use someone else's CV"
    assert client.post("/sessions", json=body | {"pack_id": "nope"}, headers=alice).status_code == 422
    assert client.post("/sessions", json=body | {"seniority": "cto"}, headers=alice).status_code == 422
    packs = {p["id"]: p for p in client.get("/packs").json()}
    assert packs["civil_service"]["levels"][:2] == ["AA", "AO"] and len(packs["civil_service"]["behaviours"]) == 9
    cs = {"pack_id": "civil_service", "role": "Policy Adviser", "seniority": "HEO", "interview_type": "mixed",
          "elements": {"behaviours": ["leadership", "working_together"], "strengths": True}, "interview_date": "2026-11-02"}
    assert client.post("/sessions", json=cs | {"seniority": "mid"}, headers=alice).status_code == 422, "grades only"
    assert client.post("/sessions", json=cs | {"elements": None}, headers=alice).status_code == 422, "behaviours required"
    assert client.post("/sessions", json=cs | {"elements": {"behaviours": ["nope"]}}, headers=alice).status_code == 422
    too_many = {"behaviours": [b["id"] for b in packs["civil_service"]["behaviours"]][:7]}
    assert client.post("/sessions", json=cs | {"elements": too_many}, headers=alice).status_code == 422
    assert client.post("/sessions", json=body | {"seniority": "HEO"}, headers=alice).status_code == 422, "no grades for generic"
    cs_id = client.post("/sessions", json=cs, headers=alice).json()["id"]  # no CV needed
    assert client.post(f"/sessions/{cs_id}/prepare", headers=alice).json() == {"questions": 4, "from_cv": 0}
    detail = client.get(f"/sessions/{cs_id}", headers=alice).json()
    assert detail["interview_date"] == "2026-11-02" and detail["elements"]["behaviours"] == ["leadership", "working_together"]

    assert client.post("/me/attribution", json={"landing": "/civil-service", "utm_source": "pcs"}, headers=alice).json() == {"ok": True}
    client.post("/me/attribution", json={"landing": "/"}, headers=alice)

    async def attribution():
        async with sessions()() as db:
            return (await repo.profile(db, "alice")).attribution

    assert asyncio.run(attribution())["landing"] == "/civil-service", "first touch wins"

    sid = client.post("/sessions", json=body, headers=alice).json()["id"]

    assert client.post(f"/sessions/{sid}/prepare", headers=bob).status_code == 404, "not bob's"
    prep = client.post(f"/sessions/{sid}/prepare", headers=alice).json()
    assert prep == {"questions": 5, "from_cv": 0}, prep
    assert client.get("/sessions", headers=alice).json() == [], "unstarted sessions aren't history"
    assert client.get(f"/sessions/{sid}", headers=bob).status_code == 404
    audio = {"file": ("r.webm", b"opus", "audio/webm")}
    assert client.post(f"/sessions/{sid}/recording", files=audio, headers=alice).status_code == 404, "not started"
    assert client.get(f"/sessions/{sid}/recording-url", headers=alice).status_code == 404, "no recording yet"

    async def start():
        async with sessions()() as db:
            assert await repo.charge(db, "alice", uuid.UUID(sid))

    asyncio.run(start())
    boom = {"file": ("r.webm", b"boom", "audio/webm")}
    assert client.post(f"/sessions/{sid}/recording", files=boom, headers=alice).json() == {"ok": True}
    failed = recording_settled(sid)
    assert failed["recording_status"] == "failed" and not failed["has_recording"], "failed conversion: no recording"
    assert not storage._store.path(f"recordings/alice/{sid}.webm").exists(), "the original is never stored"
    assert client.post(f"/sessions/{sid}/recording", files=audio, headers=alice).json() == {"ok": True}
    assert client.get("/sessions", headers=alice).json()[0]["status"] == "live"
    ready = recording_settled(sid)
    assert ready["has_recording"] and ready["recording_status"] == "ready"
    assert client.get(f"/sessions/{sid}/recording-url", headers=bob).status_code == 404, "not bob's"
    played = client.get(client.get(f"/sessions/{sid}/recording-url", headers=alice).json()["url"].removeprefix("http://testserver"))
    assert played.content == b"anon:opus", "only the anonymized recording is stored and played"

    # soft delete: hidden everywhere, but row and file are kept
    cv2 = asyncio.run(add_cv("alice"))
    assert client.delete(f"/cv/{cv2}", headers=bob).status_code == 404, "not bob's"
    assert client.delete(f"/cv/{cv2}", headers=alice).json() == {"ok": True}
    assert client.delete(f"/cv/{cv2}", headers=alice).status_code == 404, "already deleted"
    assert cv2 not in [c["id"] for c in client.get("/cvs", headers=alice).json()]
    assert client.post("/sessions", json=body | {"cv_id": cv2}, headers=alice).status_code == 422, "deleted CV unusable"

    async def still_stored():
        async with sessions()() as db:
            row = await db.get(Cv, uuid.UUID(cv2))
            return row is not None and row.deleted_at is not None

    assert asyncio.run(still_stored()), "row kept, marked deleted"

    assert client.delete(f"/sessions/{sid}", headers=alice).json() == {"ok": True}
    assert client.get("/sessions", headers=alice).json() == [] and client.get(f"/sessions/{sid}", headers=alice).status_code == 404
    assert storage._store.path(f"recordings/alice/{sid}.webm").exists(), "recording kept"

    key = f"recordings/alice/{sid}.webm"
    url = asyncio.run(storage._store.signed_url(key)).removeprefix("http://testserver")
    assert client.get(url).content == b"anon:opus"
    assert client.get(url.replace("sig=", "sig=0")).status_code == 404, "tampered signature"
    print("api PASS")


def test_share():
    asyncio.run(fresh_db("share.db"))
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api._user] = lambda authorization=Header(""): authorization.removeprefix("Bearer ") or "anon"
    client = TestClient(app)
    alice, bob = {"Authorization": "Bearer alice"}, {"Authorization": "Bearer bob"}
    report = {
        "status": "scored", "overall_score": 84, "verdict": "Hire", "top_strength": "impact",
        "dimensions": {"impact": 4.5, "structure": 3.0}, "delivery": {"wpm": 140, "fillers_per_min": 1.2, "avg_answer_s": 90},
        "answers": [{"answer_text": "I led the   migration to Postgres and cut costs by 30 percent.", "turns": []}],
    }

    async def setup():
        async with sessions()() as db:
            cv = await repo.add_cv(db, "alice", file_name="cv.pdf", raw_text="SECRET CV TEXT", cv_profile={"name": "Prashant Raj Bista"})
            row = await repo.create_session(db, "alice", **new_session_fields(cv_id=cv.id, jd_text="SECRET JD"))
            unscored = await repo.create_session(db, "alice", **new_session_fields())
            await repo.update_session(db, row.id, status="scored", report=report, record={"turns": [{"text": "SECRET TURN"}]})
            return str(row.id), str(unscored.id)

    sid, unscored = asyncio.run(setup())
    detail = client.get(f"/sessions/{sid}", headers=alice).json()
    assert detail["suggested_name"] == "PR" and detail["share"]["slug"] is None

    choices = {"name": "PR", "show_skills": False, "quote": "i led the migration to postgres"}
    assert client.put(f"/sessions/{unscored}/share", json=choices, headers=alice).status_code == 404, "unscored"
    assert client.put(f"/sessions/{sid}/share", json=choices, headers=bob).status_code == 404, "not bob's"
    fake = choices | {"quote": "I single-handedly saved the company"}
    assert client.put(f"/sessions/{sid}/share", json=fake, headers=alice).status_code == 422, "quote must be said"

    slug = client.put(f"/sessions/{sid}/share", json=choices, headers=alice).json()["slug"]
    card = client.get(f"/share/{slug}").json()  # no auth header: public
    assert card["score"] == 84 and card["name"] == "PR" and card["skills"] is None and card["delivery"]["wpm"] == 140
    public = str(card)
    assert "SECRET" not in public and "alice" not in public, "no transcript, CV, JD or account in the card"
    assert client.put(f"/sessions/{sid}/share", json=choices | {"show_name": False}, headers=alice).json()["slug"] == slug
    assert client.get(f"/share/{slug}").json()["name"] is None, "update applies, same link"

    assert client.delete(f"/sessions/{sid}/share", headers=alice).json() == {"ok": True}
    assert client.get(f"/share/{slug}").status_code == 404, "revoked"
    slug2 = client.put(f"/sessions/{sid}/share", json=choices, headers=alice).json()["slug"]
    assert slug2 != slug and client.get(f"/share/{slug}").status_code == 404, "re-share gets a new link"
    client.delete(f"/sessions/{sid}", headers=alice)
    assert client.get(f"/share/{slug2}").status_code == 404, "deleted session's card is gone"
    print("share PASS")


def test_billing():
    from server import billing
    from server.config import get_settings

    asyncio.run(fresh_db("billing.db"))
    settings = get_settings()
    settings.payment_provider = "stripe"
    settings.stripe_webhook_secret = "whsec_test"
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api._user] = lambda authorization=Header(""): authorization.removeprefix("Bearer ") or "anon"
    client = TestClient(app)

    def hook(event_id, product="credits_5", session="cs_1", type_="checkout.session.completed", paid="paid", secret="whsec_test"):
        body = json.dumps({"id": event_id, "type": type_, "data": {"object": {
            "id": session, "payment_status": paid, "client_reference_id": "alice", "amount_total": 900, "currency": "usd",
            "metadata": {"user_id": "alice", "product": product},
        }}}).encode()
        t = int(time.time())
        sig = hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
        return client.post("/billing/webhook", content=body, headers={"stripe-signature": f"t={t},v1={sig}"})

    me = lambda: client.get("/me", headers={"Authorization": "Bearer alice"}).json()  # noqa: E731
    assert me()["credits"] == 2
    assert hook("evt_1").status_code == 200 and me()["credits"] == 7, "5 credits granted"
    assert hook("evt_1").status_code == 200 and me()["credits"] == 7, "resent event: no double grant"
    hook("evt_2", type_="checkout.session.async_payment_succeeded")  # same checkout, second event type
    assert me()["credits"] == 7, "one grant per checkout"
    assert hook("evt_3", secret="whsec_forged", session="cs_2").status_code == 400, "forged signature"
    hook("evt_4", session="cs_3", paid="unpaid")
    hook("evt_5", session="cs_4", type_="invoice.paid")
    assert me()["credits"] == 7, "unpaid and unrelated events grant nothing"

    hook("evt_6", product="pass_30", session="cs_5")
    hook("evt_7", product="pass_30", session="cs_6")

    async def pass_days():  # own engine: the app's pooled connections belong to the TestClient's loop
        engine = make_engine(f"sqlite+aiosqlite:///{TMP / 'billing.db'}")
        async with engine.connect() as conn:
            until = (await conn.execute(Profile.__table__.select().where(Profile.user_id == "alice"))).one().pass_until
        await engine.dispose()
        return (repo._aware(until) - datetime.now(UTC)).days

    assert me()["has_pass"] and 59 <= asyncio.run(pass_days()) <= 60, "two passes stack to ~60 days"

    calls = []

    async def fake_checkout(_settings, uid, product):
        calls.append((uid, product.id))
        return {"provider": "stripe", "url": "https://checkout.stripe.test/x"}

    billing.create_checkout, real = fake_checkout, billing.create_checkout
    try:
        assert client.post("/billing/checkout", json={"product": "nope"}, headers={"Authorization": "Bearer alice"}).status_code == 422
        r = client.post("/billing/checkout", json={"product": "pass_30"}, headers={"Authorization": "Bearer alice"})
        assert r.json() == {"provider": "stripe", "url": "https://checkout.stripe.test/x"} and calls == [("alice", "pass_30")]
    finally:
        billing.create_checkout = real
    assert [p["id"] for p in client.get("/billing/products").json()] == ["credits_5", "pass_30"]
    print("billing (stripe) PASS")


def test_paddle():
    from server.billing import paddle_provider
    from server.config import get_settings

    asyncio.run(fresh_db("paddle.db"))
    s = get_settings()
    s.payment_provider, s.paddle_env, s.paddle_api_key = "paddle", "sandbox", "pdl_sdbx_test"
    s.paddle_webhook_secret, s.paddle_price_credits_5, s.paddle_price_pass_30 = "pdl_ntfset_test", "pri_five", "pri_pass"
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api._user] = lambda authorization=Header(""): authorization.removeprefix("Bearer ") or "anon"
    client = TestClient(app)
    alice = {"Authorization": "Bearer alice"}

    def hook(event_id, txn="txn_1", product="credits_5", price="pri_five", type_="transaction.completed", secret="pdl_ntfset_test", ts=None):
        body = json.dumps({"event_id": event_id, "event_type": type_, "data": {
            "id": txn, "status": "completed", "currency_code": "USD", "custom_data": {"user_id": "alice", "product": product},
            "items": [{"price": {"id": price}, "quantity": 1}], "details": {"totals": {"grand_total": "900"}},
        }}).encode()
        ts = ts or int(time.time())
        h1 = hmac.new(secret.encode(), f"{ts}:".encode() + body, hashlib.sha256).hexdigest()
        return client.post("/billing/webhook", content=body, headers={"paddle-signature": f"ts={ts};h1={h1}"})

    me = lambda: client.get("/me", headers=alice).json()  # noqa: E731
    assert hook("evt_1").status_code == 200 and me()["credits"] == 7, "5 credits granted"
    assert hook("evt_1").status_code == 200 and hook("evt_2").status_code == 200 and me()["credits"] == 7, "resent/same txn: once"
    assert hook("evt_3", txn="txn_2", secret="pdl_ntfset_forged").status_code == 400, "forged"
    assert hook("evt_4", txn="txn_3", ts=int(time.time()) - 3600).status_code == 400, "stale (replay)"
    hook("evt_5", txn="txn_4", type_="transaction.updated")
    hook("evt_6", txn="txn_5", product="pass_30", price="pri_five")  # claims the pass but paid the $9 price
    assert me()["credits"] == 7 and not me()["has_pass"], "other events and mismatched products grant nothing"
    hook("evt_7", txn="txn_6", product="pass_30", price="pri_pass")
    assert me()["has_pass"], "pass granted"

    sent = []

    class FakeResponse:
        status_code = 201
        text = ""

        def json(self):
            return {"data": {"id": "txn_new"}}

    class FakeHttp:
        async def post(self, url, json=None, headers=None):
            sent.append((url, json, headers))
            return FakeResponse()

    real = paddle_provider.shared_client
    paddle_provider.shared_client = lambda: FakeHttp()
    try:
        r = client.post("/billing/checkout", json={"product": "credits_5"}, headers=alice).json()
    finally:
        paddle_provider.shared_client = real
    url, body, headers = sent[0]
    assert r == {"provider": "paddle", "transaction_id": "txn_new"}
    assert url == "https://sandbox-api.paddle.com/transactions" and headers["Authorization"] == "Bearer pdl_sdbx_test"
    assert body == {"items": [{"price_id": "pri_five", "quantity": 1}], "custom_data": {"user_id": "alice", "product": "credits_5"}}
    print("billing (paddle) PASS")


async def test_purge():
    from server.purge import RETENTION_DAYS, purge

    engine = await fresh_db("purge.db")
    store = LocalStore(str(TMP / "purge-blobs"), "secret", "http://gw")
    old = datetime.now(UTC) - timedelta(days=RETENTION_DAYS + 1)
    recent = datetime.now(UTC) - timedelta(days=1)
    async with sessions()() as db:
        for key in ("cvs/u/gone.pdf", "cvs/u/kept.pdf", "recordings/u/a.webm", "recordings/u/b.webm", "recordings/u/c.webm"):
            await store.put(key, b"x", "application/octet-stream")
        gone_cv = await repo.add_cv(db, "u", file_name="gone.pdf", storage_key="cvs/u/gone.pdf", raw_text="x")
        kept_cv = await repo.add_cv(db, "u", file_name="kept.pdf", storage_key="cvs/u/kept.pdf", raw_text="x")
        a = await repo.create_session(db, "u", **new_session_fields(cv_id=gone_cv.id))  # deleted long ago
        b = await repo.create_session(db, "u", **new_session_fields())  # kept, but its recording is old
        c = await repo.create_session(db, "u", **new_session_fields())  # recent: untouched
        ids = (a.id, b.id, c.id)
        await repo.update_session(db, a.id, recording_key="recordings/u/a.webm", deleted_at=old)
        await repo.update_session(db, b.id, recording_key="recordings/u/b.webm", created_at=old)
        await repo.update_session(db, c.id, recording_key="recordings/u/c.webm", created_at=recent)
        gone_cv.deleted_at, kept_cv.deleted_at = old, recent  # kept_cv: deleted, but inside the window
        await db.commit()

        counts = await purge(db, store)
        assert counts == {"sessions": 1, "cvs": 1, "recordings": 1}, counts
        assert await db.get(InterviewSession, ids[0], populate_existing=True) is None
        b_row = await db.get(InterviewSession, ids[1], populate_existing=True)
        assert b_row is not None and b_row.recording_key is None, "old recording removed, interview kept"
        assert (await db.get(InterviewSession, ids[2], populate_existing=True)).recording_key, "recent recording kept"
        assert not store.path("recordings/u/a.webm").exists() and not store.path("recordings/u/b.webm").exists()
        assert store.path("recordings/u/c.webm").exists() and store.path("cvs/u/kept.pdf").exists()
        assert not store.path("cvs/u/gone.pdf").exists()
        assert await purge(db, store) == {"sessions": 0, "cvs": 0, "recordings": 0}, "idempotent"
    await engine.dispose()
    print("purge PASS")


def test_contact():
    asyncio.run(fresh_db("contact.db"))
    api._contact_times.clear()
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    ok = {"name": "Asha", "email": "asha@example.com", "topic": "problem", "message": "The mic check never turns green."}

    assert client.post("/contact", json=ok).json() == {"ok": True}
    assert client.post("/contact", json=ok | {"email": "not-an-email"}).status_code == 422
    assert client.post("/contact", json=ok | {"message": "hi"}).status_code == 422, "too short"
    assert client.post("/contact", json=ok | {"topic": "spam"}).status_code == 422
    assert client.post("/contact", json=ok | {"website": "http://spam"}).json() == {"ok": True}, "bot gets a fake ok"

    async def stored():  # own engine: the app's pooled connections belong to the TestClient's loop
        engine = make_engine(f"sqlite+aiosqlite:///{TMP / 'contact.db'}")
        async with engine.connect() as conn:
            rows = (await conn.execute(ContactMessage.__table__.select())).all()
        await engine.dispose()
        return rows

    rows = asyncio.run(stored())
    assert len(rows) == 1 and rows[0].email == "asha@example.com" and rows[0].user_id is None, "only the real message"
    for _ in range(3):
        client.post("/contact", json=ok)
    assert client.post("/contact", json=ok).status_code == 200  # 5th in the hour
    assert client.post("/contact", json=ok).status_code == 429, "rate limited"
    print("contact PASS")


async def main():
    await test_credits()
    await test_purge()
    await test_local_store()


if __name__ == "__main__":
    asyncio.run(main())
    test_api()
    test_share()
    test_billing()
    test_paddle()
    test_contact()
