import logging
import time

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server.adapters.tts.kokoro_adapter import KokoroAdapter
from server.config import get_settings, resolve_voice
from server.logging_config import setup_logging

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI()
_adapter = KokoroAdapter(voice=settings.tts_voice, voices=tuple(settings.tts_voices), speed=settings.tts_speed)
logger.info("TTS service ready: voice=%s", settings.tts_voice)


class SynthesizeRequest(BaseModel):
    text: str
    voice: str | None = None


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
