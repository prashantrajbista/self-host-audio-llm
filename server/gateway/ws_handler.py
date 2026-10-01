import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass
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
RESUME_WINDOW_S = 60  # a dropped interview waits this long for the same tab to reconnect before it's scored
HANGUP_CODES = (1000, 1001)  # the client hung up or closed the tab: finish now, nobody is coming back
RESUME_LINE = (
    "The call dropped for a moment and the candidate just reconnected. In one short sentence say you got cut off, "
    "then briefly repeat the question you were on, or, if they were mid-answer, ask them to pick up where they "
    "left off. Don't call next_question for this."
)
# A candidate gone quiet after a question. Each step waits this long after the previous prompt finished playing;
# any speech, or a new question, starts over. Seconds are cumulative: ~20s, ~45s, ~90s.
NUDGES = (
    (20, "The candidate has been quiet for a while. In one short sentence, check in gently: tell them to take their "
     "time, and offer to repeat or rephrase the question. Don't call next_question."),
    (25, "The candidate is still quiet. In one short sentence, offer to come back to this question later or move on. "
     "Don't call next_question yet."),
    (45, "The candidate hasn't answered for over a minute. Say briefly that you'll move on, then call next_question."),
)
IDLE_END_S = 180  # no speech at all from the candidate for this long ends the call (frees the slot, stops API spend)
IDLE_END = (
    "The candidate has been silent for several minutes. In one short sentence, say you'll stop the interview here "
    "and they can start a new one any time. Don't call next_question."
)


@dataclass
class _Call:
    """A paid interview's state, which outlives one connection so a dropped call can resume."""

    uid: str
    interview: Interview
    session: VoiceSession
    audio_started_at: float | None = None
    task: asyncio.Task | None = None  # live: the connection's task; parked: the timer that finishes it


_active_sessions = 0
_background: set[asyncio.Task] = set()  # strong refs: a bare create_task can be garbage-collected mid-run
# ponytail: in-process only, so a gateway restart drops parked calls (they're never scored); fine with one gateway
_live: dict[str, _Call] = {}
_parked: dict[str, _Call] = {}


def _spawn(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background.add(task)
    task.add_done_callback(_background.discard)
    return task


async def websocket_endpoint(ws: WebSocket) -> None:
    global _active_sessions
    await ws.accept()
    client = f"{ws.client.host}:{ws.client.port}" if ws.client else "unknown"
    settings = get_settings()
    # refuse rather than admit: past capacity every call degrades, not just the newest one.
    # A reconnecting interview is let in: its slot was only freed by the drop.
    sid = ws.query_params.get("session_id")
    resuming = sid in _parked or sid in _live
    if _active_sessions >= settings.max_sessions and not resuming:
        logger.warning("at capacity (%d sessions), refusing %s", _active_sessions, client)
        await ws.close(code=BUSY_CLOSE_CODE, reason="busy")
        return
    _active_sessions += 1
    try:
        await _run_session(ws, client, settings)
    finally:
        _active_sessions -= 1


def _new_session(ws: WebSocket, settings: Settings, agent) -> VoiceSession:
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
    return VoiceSession(
        stt=get_stt(settings),
        llm=get_llm(settings),
        tts=get_tts(settings),
        vad=VAD(threshold=settings.vad_threshold),
        send_json=ws.send_json,
        send_bytes=ws.send_bytes,
        voice=voice,
        agent=agent,
    )


async def _run_session(ws: WebSocket, client: str, settings: Settings) -> None:
    logger.info("client connected: %s", client)
    call = None
    watcher = None
    interview_id = ws.query_params.get("session_id")
    if interview_id:
        uid = await verify_token(settings, ws.query_params.get("token", ""))
        call = await _resume(interview_id, uid)
        opening = RESUME_LINE
        if call is None:
            interview, refusal = await _start_interview(ws.query_params, uid, settings, ws.send_json)
            if interview is None:
                await ws.close(code=refusal, reason="interview refused")
                return
            call = _Call(uid, interview, _new_session(ws, settings, interview.agent()))
            opening = await interview.kickoff()
        else:
            logger.info("interview %s: resumed", interview_id)
        call.task = asyncio.current_task()
        call.interview.emit = ws.send_json
        call.session.attach(ws.send_json, ws.send_bytes)
        _live[interview_id] = call
        session = call.session
        await session.open(opening)
        watcher = asyncio.create_task(_watch_interview(ws, session, call.interview, interview_id))
    else:
        session = _new_session(ws, settings, get_agent(ws.query_params.get("agent"), settings.agent))

    buffer = bytearray()
    audio_started_at = call.audio_started_at if call else None  # first mic audio: the client starts recording with the mic
    close_code = None  # set when the client went away; None = we crashed or closed it
    taken_over = False
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
                elif control.get("type") == "mute":
                    session.muted = bool(control.get("muted"))
    except WebSocketDisconnect as e:
        close_code = e.code
        logger.info("client disconnected: %s (code %s)", client, e.code)
    except asyncio.CancelledError:
        # a reconnect of this interview arrived before this connection noticed it was dead
        if not call or _live.get(interview_id) is call:
            raise
        taken_over = True
    except Exception:
        logger.exception("session crashed: %s", client)
    finally:
        if watcher:
            watcher.cancel()
        if call is None:
            session.close()
        else:
            call.audio_started_at = audio_started_at
            await _hand_off(settings, interview_id, call, close_code, taken_over)


async def _resume(interview_id: str, uid: str | None) -> _Call | None:
    """The caller's own dropped interview, if it can still continue."""
    call = _live.get(interview_id)
    if call and call.uid == uid:
        del _live[interview_id]
        call.task.cancel()  # the old connection hands the call over (see _run_session) and ends
        await asyncio.wait([call.task])
        return call
    call = _parked.get(interview_id)
    if call and call.uid == uid:
        del _parked[interview_id]
        call.task.cancel()  # the timer that would have finished it
        return call
    return None


async def _hand_off(settings: Settings, interview_id: str, call: _Call, close_code: int | None, taken_over: bool) -> None:
    """Connection over: finish the interview, or park it for a reconnect if the call just dropped."""
    if _live.get(interview_id) is call:
        del _live[interview_id]
    if taken_over:
        await call.session.detach()
        return
    dropped = close_code is not None and close_code not in HANGUP_CODES
    if dropped and not call.interview.ended and not call.interview.overtime():
        logger.info("interview %s: dropped, waiting %ds for a reconnect", interview_id, RESUME_WINDOW_S)
        await call.session.detach()
        _parked[interview_id] = call
        call.task = _spawn(_expire(settings, interview_id, call))
        return
    _finish(settings, interview_id, call)


async def _expire(settings: Settings, interview_id: str, call: _Call) -> None:
    await asyncio.sleep(RESUME_WINDOW_S)
    if _parked.get(interview_id) is call:
        del _parked[interview_id]
        logger.info("interview %s: no reconnect", interview_id)
        _finish(settings, interview_id, call)


def _finish(settings: Settings, interview_id: str, call: _Call) -> None:
    call.session.close()
    record = call.interview.record(call.session.turns, call.audio_started_at)
    _spawn(_finish_interview(settings, uuid.UUID(interview_id), record))


async def _start_interview(params, uid: str | None, settings: Settings, emit) -> tuple[Interview | None, int]:
    """Signed-in interview: the caller must own a prepared, unstarted session; starting it charges for it."""
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
    """Prompt a candidate who has gone quiet, and close the call once the interviewer ends it (after the goodbye
    plays), the candidate stays silent too long, or at the hard time limit."""
    # from the interview's start, not this connection's: a resumed call keeps its original time limit
    deadline = interview.started_at + (interview.pack["flow"]["duration_min"] + INTERVIEW_GRACE_MIN) * 60
    step, heard, question = 0, session.last_heard, interview.index
    while not interview.ended and time.time() < deadline:
        await asyncio.sleep(0.5)
        if session.last_heard != heard or interview.index != question:  # they spoke, or a new question: start over
            step, heard, question = 0, session.last_heard, interview.index
        silence = session.silence_s()
        if silence and time.monotonic() - session.last_heard >= IDLE_END_S:
            interview.idle = interview.ended = True
            await session.open(IDLE_END)
            break
        if step < len(NUDGES) and silence >= NUDGES[step][0] and time.time() >= interview.quiet_until:
            # the client shows why it may be quiet (muted, or a mic that hears nothing); muted = no spoken nudge
            await ws.send_json({"type": "silence", "data": {"muted": session.muted}})
            if not session.muted:
                await session.open(NUDGES[step][1])
            step += 1
    await session.drain()
    completed = interview.ended and not interview.idle
    await ws.send_json({"type": "interview_end", "data": {"id": interview_id, "completed": completed}})
    await ws.close()
