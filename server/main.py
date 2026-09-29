import io
import json
import re
from pathlib import Path
from contextlib import asynccontextmanager

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException, Response, WebSocket

from server.agent.interview import load_packs
from server.agent.scoring import report_path
from server.config import get_settings
from server.gateway.factory import get_stt, get_tts
from server.gateway.ws_handler import websocket_endpoint
from server.logging_config import setup_logging
from server.vad import vad

setup_logging(get_settings().log_level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # load + warm the cached STT/TTS models at boot, not on the first WS connection
    settings = get_settings()
    get_stt(settings)
    get_tts(settings)
    vad.preload()  # per-connection VADs copy this, so a connect never reads the model from disk
    load_packs(settings.packs_dir)  # an invalid interview pack fails the boot, not a call
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"ok": True}  # lifespan loads the models before serving: reachable = ready


@app.websocket("/ws")
async def ws_route(websocket: WebSocket):
    await websocket_endpoint(websocket)


@app.get("/interviews/{interview_id}/report")
async def interview_report(interview_id: str):
    """Feedback report: {"status": "scoring"} until grading finishes, then the full report (or "failed")."""
    if not re.fullmatch(r"[0-9a-f]{32}", interview_id):  # ids are uuid4 hex; also blocks path traversal
        raise HTTPException(status_code=404, detail="unknown interview")
    record = Path(get_settings().interviews_dir) / f"{interview_id}.json"
    if report_path(record).exists():
        return json.loads(report_path(record).read_text())
    if record.exists():
        return {"status": "scoring"}
    raise HTTPException(status_code=404, detail="unknown interview")


_previews: dict[str, bytes] = {}

# Preview lines written to each voice's personality (matches the client's voice descriptions).
# Voices without an entry fall back to a generic intro.
_PREVIEW_LINES = {
    "af_heart": "Hey, I'm Heart. Pull up a chair and tell me what's on your mind. I'm all ears.",
    "af_bella": "Hi, I'm Bella! Got a big idea or a tiny question? Either way, let's make it fun!",
    "am_michael": "Hello, I'm Michael. Take your time. We'll work through it together, one step at a time.",
    "am_fenrir": "I'm Fenrir. Whatever you're facing, we'll take it on steady and sure.",
}


@app.get("/voices/{voice}/preview")
async def voice_preview(voice: str):
    """Short WAV sample of a selectable voice for the client's voice picker; cached after first synth."""
    settings = get_settings()
    if voice not in settings.tts_voices:
        raise HTTPException(status_code=404, detail="unknown voice")
    if voice not in _previews:
        name = voice.split("_", 1)[-1].capitalize()
        line = _PREVIEW_LINES.get(voice, f"Hi, I'm {name}. Nice to meet you.")
        pcm = bytearray()
        async for chunk in get_tts(settings).synthesize_stream(line, voice=voice):
            pcm.extend(chunk)
        buf = io.BytesIO()
        sf.write(buf, np.frombuffer(bytes(pcm), dtype=np.int16), 24000, format="WAV", subtype="PCM_16")
        _previews[voice] = buf.getvalue()
    return Response(_previews[voice], media_type="audio/wav")
