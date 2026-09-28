import io
from contextlib import asynccontextmanager

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException, Response, WebSocket

from server.config import get_settings
from server.gateway.factory import get_stt, get_tts
from server.gateway.ws_handler import websocket_endpoint
from server.logging_config import setup_logging

setup_logging(get_settings().log_level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # load + warm the cached STT/TTS models at boot, not on the first WS connection
    settings = get_settings()
    get_stt(settings)
    get_tts(settings)
    yield


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def ws_route(websocket: WebSocket):
    await websocket_endpoint(websocket)


_previews: dict[str, bytes] = {}


@app.get("/voices/{voice}/preview")
async def voice_preview(voice: str):
    """Short WAV sample of a selectable voice for the client's voice picker; cached after first synth."""
    settings = get_settings()
    if voice not in settings.tts_voices:
        raise HTTPException(status_code=404, detail="unknown voice")
    if voice not in _previews:
        name = voice.split("_", 1)[-1].capitalize()
        line = f"Hi, I'm {name}. How can I help today?"
        pcm = bytearray()
        async for chunk in get_tts(settings).synthesize_stream(line, voice=voice):
            pcm.extend(chunk)
        buf = io.BytesIO()
        sf.write(buf, np.frombuffer(bytes(pcm), dtype=np.int16), 24000, format="WAV", subtype="PCM_16")
        _previews[voice] = buf.getvalue()
    return Response(_previews[voice], media_type="audio/wav")
