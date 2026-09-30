import asyncio
import json
import logging
import time
import uuid
from datetime import UTC, datetime

from fastapi import WebSocket, WebSocketDisconnect

from server.agent.agents import get_agent
from server.agent.cv import summary
from server.agent.interview import Interview, load_packs
from server.agent.scoring import score_record
from server.auth import verify_token
from server.config import Settings, get_settings, resolve_voice
from server.gateway.factory import get_llm, get_stt, get_tts
from server.gateway.session import VoiceSession
from server.store import repo
from server.store.db import sessions
from server.vad.vad import VAD

logger = logging.getLogger(__name__)

FRAME_BYTES = 640  # 20ms of mono PCM16 @ 16kHz


BUSY_CLOSE_CODE = 1013  # "try again later": the client shows "all lines busy" instead of a dropped call
POLICY_CLOSE_CODE = 1008  # not signed in, not your interview, or already started
NO_CREDITS_CLOSE_CODE = 4402  # the client shows the paywall
INTERVIEW_GRACE_MIN = 2  # hard stop this long after the pack's duration, if the interviewer never wraps up

_active_sessions = 0
_scoring: set[asyncio.Task] = set()  # strong refs: a bare create_task can be garbage-collected mid-run


async def websocket_endpoint(ws: WebSocket) -> None:
    global _active_sessions
    await ws.accept()
    client = f"{ws.client.host}:{ws.client.port}" if ws.client else "unknown"
    settings = get_settings()
    # refuse rather than admit: past capacity every call degrades, not just the newest one
    if _active_sessions >= settings.max_sessions:
        logger.warning("at capacity (%d sessions), refusing %s", _active_sessions, client)
        await ws.close(code=BUSY_CLOSE_CODE, reason="busy")
        return
    _active_sessions += 1
    try:
        await _run_session(ws, client, settings)
    finally:
        _active_sessions -= 1


async def _run_session(ws: WebSocket, client: str, settings: Settings) -> None:
    logger.info("client connected: %s", client)
    interview = None
    interview_id = ws.query_params.get("session_id")
    if interview_id:
        interview, refusal = await _start_interview(ws.query_params, settings, ws.send_json)
        if interview is None:
            await ws.close(code=refusal, reason="interview refused")
            return
    agent = interview.agent() if interview else get_agent(ws.query_params.get("agent"), settings.agent)
    # client's pick wins, then the agent's own voice, then the configured default
    voice = resolve_voice(settings, ws.query_params.get("voice") or agent.voice)
    logger.debug(
        "session backends: stt=%s llm=%s tts=%s voice=%s agent=%s",
        settings.stt_backend,
        settings.llm_backend,
        settings.tts_backend,
        voice,
        agent.name,
    )
    session = VoiceSession(
        stt=get_stt(settings),
        llm=get_llm(settings),
        tts=get_tts(settings),
        vad=VAD(threshold=settings.vad_threshold),
        send_json=ws.send_json,
        send_bytes=ws.send_bytes,
        voice=voice,
        agent=agent,
    )

    watcher = None
    if interview:
        await session.open(await interview.kickoff())
        watcher = asyncio.create_task(_watch_interview(ws, session, interview, interview_id))

    buffer = bytearray()
    audio_started_at = None  # first mic audio: the client starts recording together with the mic
    try:
        while True:
            # binary frames = mic audio; text frames = JSON control messages from the client
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(message.get("code", 1000))
            if message.get("bytes") is not None:
                audio_started_at = audio_started_at or time.time()
                buffer.extend(message["bytes"])
                while len(buffer) >= FRAME_BYTES:
                    frame = bytes(buffer[:FRAME_BYTES])
                    del buffer[:FRAME_BYTES]
                    await session.handle_audio_frame(frame)
            elif message.get("text") is not None:
                control = json.loads(message["text"])
                if control.get("type") == "interrupt":
                    await session.interrupt()
    except WebSocketDisconnect:
        logger.info("client disconnected: %s", client)
    except Exception:
        logger.exception("session crashed: %s", client)
    finally:
        if watcher:
            watcher.cancel()
        session.close()
        if interview:
            task = asyncio.create_task(_finish_interview(settings, uuid.UUID(interview_id), interview.record(session.turns, audio_started_at)))
            _scoring.add(task)
            task.add_done_callback(_scoring.discard)


async def _start_interview(params, settings: Settings, emit) -> tuple[Interview | None, int]:
    """Signed-in interview: the caller must own a prepared, unstarted session; starting it charges for it."""
    uid = await verify_token(settings, params.get("token", ""))
    try:
        session_id = uuid.UUID(params["session_id"])
    except ValueError:
        return None, POLICY_CLOSE_CODE
    async with sessions()() as db:
        row = await repo.get_session(db, uid, session_id) if uid else None
        pack = load_packs(settings.packs_dir).get(row.pack_id) if row else None
        if not row or row.status != "created" or not row.plan or not pack:
            logger.warning("interview refused: session=%s user=%s", session_id, uid)
            return None, POLICY_CLOSE_CODE
        if not await repo.charge(db, uid, session_id):
            return None, NO_CREDITS_CLOSE_CODE
        cv = await repo.get_cv(db, uid, row.cv_id) if row.cv_id else None
    return Interview(
        pack, row.plan, row.role, row.seniority, row.interview_type, emit,
        cv_summary=summary(cv.cv_profile) if cv and cv.cv_profile else "", jd_text=row.jd_text or "",
    ), 0


async def _finish_interview(settings: Settings, session_id: uuid.UUID, record: dict) -> None:
    """Store the transcript, score it, store the report. Empty or failed interviews get their credit back."""
    try:
        async with sessions()() as db:
            ended = {"record": record, "ended_at": datetime.now(UTC)}
            if not any(t["role"] == "user" for t in record["turns"]):
                await repo.update_session(db, session_id, **ended, status="abandoned")
                await repo.refund(db, session_id)
                logger.info("interview %s: abandoned", session_id)
                return
            await repo.update_session(db, session_id, **ended, status="scoring")
            report = await score_record(record, settings)
            fields = {"status": report["status"], "report": report}
            if report["status"] == "scored":
                fields |= {"overall_score": report["overall_score"], "verdict": report["verdict"]}
            await repo.update_session(db, session_id, **fields)
            if report["status"] == "failed":
                await repo.refund(db, session_id)
        logger.info("interview %s: %s", session_id, report["status"])
    except Exception:
        logger.exception("finishing interview %s failed", session_id)


async def _watch_interview(ws: WebSocket, session: VoiceSession, interview: Interview, interview_id: str) -> None:
    """Close the call once the interviewer ends it (after the goodbye plays), or at the hard time limit."""
    deadline = time.monotonic() + (interview.pack["flow"]["duration_min"] + INTERVIEW_GRACE_MIN) * 60
    while not interview.ended and time.monotonic() < deadline:
        await asyncio.sleep(0.5)
    await session.drain()
    await ws.send_json({"type": "interview_end", "data": {"id": interview_id, "completed": interview.ended}})
    await ws.close()
