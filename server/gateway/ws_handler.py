import asyncio
import json
import logging
import time
import uuid
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect

from server.agent.agents import get_agent
from server.agent.interview import INTERVIEW_TYPES, KICKOFF, SENIORITIES, Interview, load_packs, plan_questions
from server.config import Settings, get_settings, resolve_voice
from server.gateway.factory import get_llm, get_stt, get_tts
from server.gateway.session import VoiceSession
from server.vad.vad import VAD

logger = logging.getLogger(__name__)

FRAME_BYTES = 640  # 20ms of mono PCM16 @ 16kHz


BUSY_CLOSE_CODE = 1013  # "try again later": the client shows "all lines busy" instead of a dropped call
POLICY_CLOSE_CODE = 1008  # bad interview parameters
INTERVIEW_GRACE_MIN = 2  # hard stop this long after the pack's duration, if the interviewer never wraps up

_active_sessions = 0


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
    if ws.query_params.get("pack"):
        interview = _make_interview(ws.query_params, settings, ws.send_json)
        if interview is None:
            await ws.close(code=POLICY_CLOSE_CODE, reason="bad interview parameters")
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

    interview_id = uuid.uuid4().hex
    watcher = None
    if interview:
        await session.open(KICKOFF)
        watcher = asyncio.create_task(_watch_interview(ws, session, interview, interview_id))

    buffer = bytearray()
    try:
        while True:
            # binary frames = mic audio; text frames = JSON control messages from the client
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(message.get("code", 1000))
            if message.get("bytes") is not None:
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
            _save_interview(settings, interview_id, interview.record(session.turns))


def _make_interview(params, settings: Settings, emit) -> Interview | None:
    pack = load_packs(settings.packs_dir).get(params.get("pack", ""))
    seniority = params.get("seniority", "mid")
    interview_type = params.get("type", "mixed")
    role = (params.get("role") or "Software Engineer").strip()[:80]
    if not pack or seniority not in SENIORITIES or interview_type not in INTERVIEW_TYPES:
        logger.warning("bad interview params: %s", dict(params))
        return None
    return Interview(pack, plan_questions(pack, interview_type, seniority), role, seniority, interview_type, emit)


async def _watch_interview(ws: WebSocket, session: VoiceSession, interview: Interview, interview_id: str) -> None:
    """Close the call once the interviewer ends it (after the goodbye plays), or at the hard time limit."""
    deadline = time.monotonic() + (interview.pack["flow"]["duration_min"] + INTERVIEW_GRACE_MIN) * 60
    while not interview.ended and time.monotonic() < deadline:
        await asyncio.sleep(0.5)
    await session.drain()
    await ws.send_json({"type": "interview_end", "data": {"id": interview_id, "completed": interview.ended}})
    await ws.close()


def _save_interview(settings: Settings, interview_id: str, record: dict) -> None:
    if not record["turns"]:
        return  # hung up before saying anything: nothing to score
    path = Path(settings.interviews_dir) / f"{interview_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2))
    logger.info("interview saved: %s", path)
