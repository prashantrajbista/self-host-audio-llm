"""HTTP API for the interview coach web client.

Every route touching user data resolves the caller from their access token (`_user`) and goes through
server.store.repo, whose queries are all scoped to that user id."""

import logging
import uuid
from pathlib import PurePath
from typing import Literal

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.agent.cv import MAX_BYTES as MAX_CV_BYTES
from server.agent.cv import CVError, check_jd, cv_questions, extract_text, structure
from server.agent.interview import cv_question_count, load_packs, plan_questions
from server.agent.scoring import scoring_llm
from server import billing
from server.auth import verify_token
from server.config import get_settings
from server.share import ShareChoices, initials, public_card, validate
from server.storage import LocalStore, get_storage
from server.store import repo
from server.store.db import get_db
from server.store.models import Cv, InterviewSession

logger = logging.getLogger(__name__)
router = APIRouter()

CV_TYPES = {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".txt": "text/plain"}
MAX_RECORDING_BYTES = 50 * 1024 * 1024  # ~25 min of opus is a few MB; generous headroom
RECORDING_URL_TTL_S = 3600


async def _user(authorization: str = Header("")) -> str:
    uid = await verify_token(get_settings(), authorization.removeprefix("Bearer ").strip())
    if not uid:
        raise HTTPException(401, "sign in again")
    return uid


def _cv_json(cv: Cv) -> dict:
    return {"id": str(cv.id), "file_name": cv.file_name, "cv_profile": cv.cv_profile, "created_at": cv.created_at.isoformat()}


def _session_json(s: InterviewSession, full: bool = False) -> dict:
    out = {
        "id": str(s.id), "pack_id": s.pack_id, "role": s.role, "seniority": s.seniority,
        "interview_type": s.interview_type, "status": s.status, "overall_score": s.overall_score,
        "verdict": s.verdict, "created_at": s.created_at.isoformat(),
    }
    if full:
        out |= {
            "report": s.report, "has_recording": bool(s.recording_key), "jd_text": s.jd_text,
            "audio_started_at": (s.record or {}).get("audio_started_at"),
            "share": {"slug": s.share_slug if s.is_public else None, "choices": s.share_fields},
        }
    return out


@router.get("/packs")
async def packs():
    return [{"id": p["id"], "name": p["name"]} for p in load_packs(get_settings().packs_dir).values()]


@router.get("/me")
async def me(uid: str = Depends(_user), db: AsyncSession = Depends(get_db)):
    p = await repo.profile(db, uid)
    return {"credits": p.credits, "has_pass": repo.has_pass(p)}


@router.get("/cvs")
async def cvs(uid: str = Depends(_user), db: AsyncSession = Depends(get_db)):
    return [_cv_json(cv) for cv in await repo.list_cvs(db, uid)]


@router.post("/cv")
async def upload_cv(file: UploadFile = File(...), uid: str = Depends(_user), db: AsyncSession = Depends(get_db)):
    """A CV file (PDF/DOCX/TXT) -> stored + structured profile the user can review."""
    data = await file.read(MAX_CV_BYTES + 1)
    try:
        raw = extract_text(file.filename or "", data)
        profile = await structure(scoring_llm(get_settings()), raw)
    except CVError as e:
        raise HTTPException(422, str(e)) from e
    ext = PurePath(file.filename or "").suffix.lower()
    key = f"cvs/{uid}/{uuid.uuid4().hex}{ext}"
    await get_storage(get_settings()).put(key, data, CV_TYPES[ext])
    cv = await repo.add_cv(db, uid, file_name=(file.filename or "cv")[:255], storage_key=key, raw_text=raw, cv_profile=profile)
    return _cv_json(cv)


@router.delete("/cv/{cv_id}")
async def delete_cv(cv_id: uuid.UUID, uid: str = Depends(_user), db: AsyncSession = Depends(get_db)):
    if not await repo.delete_cv(db, uid, cv_id):
        raise HTTPException(404, "unknown CV")
    return {"ok": True}


class NewSession(BaseModel):
    pack_id: str
    role: str = Field(min_length=1, max_length=80)
    seniority: Literal["junior", "mid", "senior"]
    interview_type: Literal["behavioral", "hr", "mixed"]
    cv_id: uuid.UUID  # required: questions are grounded in the candidate's CV
    jd_text: str | None = Field(None, max_length=8000)


@router.post("/sessions")
async def create_session(body: NewSession, uid: str = Depends(_user), db: AsyncSession = Depends(get_db)):
    """Create an interview (checks the user can pay; the credit is taken when it goes live)."""
    if body.pack_id not in load_packs(get_settings().packs_dir):
        raise HTTPException(422, "unknown interview type")
    jd_text = (body.jd_text or "").strip() or None
    if jd_text:
        try:
            await check_jd(scoring_llm(get_settings()), jd_text)
        except CVError as e:
            raise HTTPException(422, str(e)) from e
    try:
        row = await repo.create_session(
            db, uid, pack_id=body.pack_id, role=body.role.strip(), seniority=body.seniority,
            interview_type=body.interview_type, cv_id=body.cv_id, jd_text=jd_text,
        )
    except repo.NoCredits as e:
        raise HTTPException(402, "You've used your mocks. Pick a plan to keep practising.") from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return {"id": str(row.id)}


@router.post("/sessions/{session_id}/prepare")
async def prepare(session_id: uuid.UUID, uid: str = Depends(_user), db: AsyncSession = Depends(get_db)):
    """Build the question plan: CV-grounded questions (when a CV is attached) + bank questions."""
    row = await repo.get_session(db, uid, session_id)
    if not row or row.status != "created":
        raise HTTPException(404, "unknown or already started interview")
    pack = load_packs(get_settings().packs_dir)[row.pack_id]
    cv_qs = []
    if row.cv_id and (cv := await repo.get_cv(db, uid, row.cv_id)) and cv.cv_profile:
        cv_qs = await cv_questions(
            scoring_llm(get_settings()), pack, cv.cv_profile, row.jd_text, row.seniority, row.role, cv_question_count(pack)
        )
    plan = plan_questions(pack, row.interview_type, row.seniority, cv_qs=cv_qs)
    await repo.set_plan(db, uid, session_id, plan)
    return {"questions": len(plan), "from_cv": len(cv_qs)}


@router.get("/sessions")
async def sessions(uid: str = Depends(_user), db: AsyncSession = Depends(get_db)):
    return [_session_json(s) for s in await repo.list_sessions(db, uid)]


@router.get("/sessions/{session_id}")
async def session(session_id: uuid.UUID, uid: str = Depends(_user), db: AsyncSession = Depends(get_db)):
    row = await repo.get_session(db, uid, session_id)
    if not row:
        raise HTTPException(404, "unknown interview")
    out = _session_json(row, full=True)
    cv = await repo.get_cv(db, uid, row.cv_id) if row.cv_id else None
    out["suggested_name"] = initials((cv.cv_profile or {}).get("name") if cv else None)
    return out


@router.put("/sessions/{session_id}/share")
async def share(session_id: uuid.UUID, choices: ShareChoices, uid: str = Depends(_user), db: AsyncSession = Depends(get_db)):
    """Publish (or update) the public card; returns its slug."""
    row = await repo.get_session(db, uid, session_id)
    if not row or row.status != "scored":
        raise HTTPException(404, "only a scored interview can be shared")
    try:
        choices = validate(choices, row.report or {})
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return {"slug": await repo.share_session(db, uid, session_id, choices.model_dump())}


@router.delete("/sessions/{session_id}/share")
async def unshare(session_id: uuid.UUID, uid: str = Depends(_user), db: AsyncSession = Depends(get_db)):
    if not await repo.unshare_session(db, uid, session_id):
        raise HTTPException(404, "unknown interview")
    return {"ok": True}


@router.get("/share/{slug}")
async def shared_card(slug: str, db: AsyncSession = Depends(get_db)):
    """Public, no sign-in: only what the owner chose to show (server/share.py)."""
    row = await repo.get_shared(db, slug)
    if not row:
        raise HTTPException(404, "not shared")
    return public_card(row)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: uuid.UUID, uid: str = Depends(_user), db: AsyncSession = Depends(get_db)):
    if not await repo.delete_session(db, uid, session_id):
        raise HTTPException(404, "unknown interview")
    return {"ok": True}


@router.post("/sessions/{session_id}/recording")
async def upload_recording(
    session_id: uuid.UUID, file: UploadFile = File(...), uid: str = Depends(_user), db: AsyncSession = Depends(get_db)
):
    row = await repo.get_session(db, uid, session_id)
    if not row or row.status == "created":
        raise HTTPException(404, "unknown or unstarted interview")
    data = await file.read(MAX_RECORDING_BYTES + 1)
    if len(data) > MAX_RECORDING_BYTES:
        raise HTTPException(413, "recording too large")
    content_type = file.content_type or "audio/webm"
    key = f"recordings/{uid}/{session_id}.{'m4a' if 'mp4' in content_type else 'webm'}"
    await get_storage(get_settings()).put(key, data, content_type)
    await repo.update_session(db, session_id, recording_key=key)
    return {"ok": True}


@router.get("/sessions/{session_id}/recording-url")
async def recording_url(session_id: uuid.UUID, uid: str = Depends(_user), db: AsyncSession = Depends(get_db)):
    """Short-lived link the browser plays the recording from (storage stays private)."""
    row = await repo.get_session(db, uid, session_id)
    if not row or not row.recording_key:
        raise HTTPException(404, "no recording")
    return {"url": await get_storage(get_settings()).signed_url(row.recording_key, RECORDING_URL_TTL_S)}


@router.get("/files/{key:path}")
async def local_file(key: str, exp: int, sig: str):
    """Serves LocalStore files behind signed, expiring URLs (development storage only)."""
    store = get_storage(get_settings())
    if not isinstance(store, LocalStore) or not store.verify(key, exp, sig):
        raise HTTPException(404, "not found")
    path = store.path(key)
    if not path.is_file():
        raise HTTPException(404, "not found")
    return FileResponse(path)


@router.get("/billing/products")
async def products():
    return [{"id": p.id, "label": p.label, "price": p.price_label} for p in billing.PRODUCTS.values()]


class CheckoutRequest(BaseModel):
    product: str


@router.post("/billing/checkout")
async def checkout(body: CheckoutRequest, uid: str = Depends(_user)):
    product = billing.PRODUCTS.get(body.product)
    if not product:
        raise HTTPException(422, "unknown product")
    try:
        return {"url": await billing.create_checkout(get_settings(), uid, product)}
    except billing.BillingError as e:
        logger.error("checkout unavailable: %s", e)
        raise HTTPException(503, "Payments aren't available right now. Try again later.") from e


@router.post("/billing/webhook")
async def webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Stripe -> us. Signature checked on the raw body; 2xx tells Stripe to stop retrying."""
    try:
        purchase = billing.parse_webhook(get_settings(), await request.body(), request.headers.get("stripe-signature", ""))
    except ValueError as e:
        raise HTTPException(400, "invalid webhook") from e
    if purchase:
        granted = await repo.grant(
            db, purchase.user_id, product=purchase.product.id, credits=purchase.product.credits,
            pass_days=purchase.product.pass_days, event_id=purchase.event_id, session_id=purchase.session_id,
            amount_total=purchase.amount_total, currency=purchase.currency,
        )
        logger.info("payment %s for %s: %s", purchase.session_id, purchase.user_id, "granted" if granted else "duplicate")
    return {"ok": True}
