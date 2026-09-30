import logging
import time

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server.config import get_settings, resolve_voice
from server.gateway.factory import build_kokoro
from server.logging_config import setup_logging

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI()
# DEVICE was previously ignored here, so the GPU compose override still synthesized on CPU
_device = settings.device if settings.device in ("cpu", "cuda") else "cpu"
_adapter = build_kokoro(settings, _device)
logger.info(
    "TTS service ready: engine=%s voice=%s device=%s workers=%d",
    settings.tts_engine, settings.tts_voice, _device, settings.tts_workers,
)


class SynthesizeRequest(BaseModel):
    text: str
    voice: str | None = None


@app.get("/health")
async def health():
    return {"ok": True}  # the model loads at import, before the app serves: reachable = ready


@app.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    logger.debug("synthesize request: %r", req.text)

    async def gen():
        start = time.monotonic()
        chunks = 0
        async for chunk in _adapter.synthesize_stream(req.text, voice=resolve_voice(settings, req.voice)):
            chunks += 1
            yield chunk
        logger.info("synthesize done (%.2fs): %d chunks", time.monotonic() - start, chunks)

    return StreamingResponse(gen(), media_type="application/octet-stream")
