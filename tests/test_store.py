"""Store, storage and API checks on a throwaway SQLite database (no Supabase, no models, no network).
Run: python -m tests.test_store
"""

import asyncio
import tempfile
import time
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
from server.store.models import Base, Cv, InterviewSession, Profile

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
    client = TestClient(app)
    alice, bob = {"Authorization": "Bearer alice"}, {"Authorization": "Bearer bob"}

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
    assert client.post(f"/sessions/{sid}/recording", files=audio, headers=alice).json() == {"ok": True}
    assert client.get("/sessions", headers=alice).json()[0]["status"] == "live"
    assert client.get(f"/sessions/{sid}", headers=alice).json()["has_recording"]
    assert client.get(f"/sessions/{sid}/recording-url", headers=bob).status_code == 404, "not bob's"
    played = client.get(client.get(f"/sessions/{sid}/recording-url", headers=alice).json()["url"].removeprefix("http://testserver"))
    assert played.content == b"opus", "signed recording URL plays the upload"

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
    assert client.get(url).content == b"opus"
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


async def main():
    await test_credits()
    await test_local_store()


if __name__ == "__main__":
    asyncio.run(main())
    test_api()
    test_share()
