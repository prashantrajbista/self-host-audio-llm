from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server.adapters.tts.kokoro_adapter import KokoroAdapter
from server.config import get_settings

app = FastAPI()
settings = get_settings()
_adapter = KokoroAdapter(voice=settings.tts_voice)


class SynthesizeRequest(BaseModel):
    text: str


@app.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    async def gen():
        async for chunk in _adapter.synthesize_stream(req.text):
            yield chunk

    return StreamingResponse(gen(), media_type="application/octet-stream")
