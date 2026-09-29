import logging
import time

from fastapi import FastAPI, Request

from server.adapters.stt.faster_whisper_adapter import FasterWhisperAdapter
from server.config import get_settings
from server.logging_config import setup_logging

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI()
_device = settings.device if settings.device in ("cpu", "cuda") else "cpu"
_adapter = FasterWhisperAdapter(
    model_size=settings.whisper_model, device=_device, workers=settings.stt_workers, cpu_threads=settings.stt_cpu_threads
)
logger.info("STT service ready: model=%s device=%s", settings.whisper_model, _device)


@app.get("/health")
async def health():
    return {"ok": True}  # the model loads at import, before the app serves: reachable = ready


@app.post("/transcribe")
async def transcribe(request: Request):
    audio = await request.body()
    logger.debug("transcribe request: %d bytes", len(audio))
    start = time.monotonic()
    text = ""
    async for event in _adapter.transcribe_stream(audio):
        if event.is_final:
            text = event.text
    elapsed = time.monotonic() - start
    logger.info("transcript (%.2fs): %r", elapsed, text)
    return {"text": text}
