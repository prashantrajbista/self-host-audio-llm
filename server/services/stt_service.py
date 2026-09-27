import logging

from fastapi import FastAPI, Request

from server.adapters.stt.faster_whisper_adapter import FasterWhisperAdapter
from server.config import get_settings
from server.logging_config import setup_logging

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI()
_device = settings.device if settings.device in ("cpu", "cuda") else "cpu"
_adapter = FasterWhisperAdapter(model_size=settings.whisper_model, device=_device)
logger.info("STT service ready: model=%s device=%s", settings.whisper_model, _device)


@app.post("/transcribe")
async def transcribe(request: Request):
    audio = await request.body()
    logger.debug("transcribe request: %d bytes", len(audio))
    text = ""
    async for event in _adapter.transcribe_stream(audio):
        if event.is_final:
            text = event.text
    logger.info("transcript: %r", text)
    return {"text": text}
