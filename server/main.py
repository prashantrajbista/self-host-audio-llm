import io
from contextlib import asynccontextmanager

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from server.agent.interview import load_packs
from server.config import get_settings
from server.gateway.factory import get_stt, get_tts
from server.gateway.api import router as api_router
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(api_router)


@app.get("/health")
async def health():
    return {"ok": True}  # lifespan loads the models before serving: reachable = ready


@app.websocket("/ws")
async def ws_route(websocket: WebSocket):
    await websocket_endpoint(websocket)


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
