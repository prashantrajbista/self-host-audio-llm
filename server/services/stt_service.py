from fastapi import FastAPI, Request

from server.adapters.stt.faster_whisper_adapter import FasterWhisperAdapter
from server.config import get_settings

app = FastAPI()
settings = get_settings()
_device = settings.device if settings.device in ("cpu", "cuda") else "cpu"
_adapter = FasterWhisperAdapter(model_size=settings.whisper_model, device=_device)


@app.post("/transcribe")
async def transcribe(request: Request):
    audio = await request.body()
    text = ""
    async for event in _adapter.transcribe_stream(audio):
        if event.is_final:
            text = event.text
    return {"text": text}
