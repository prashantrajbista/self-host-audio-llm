from collections.abc import AsyncIterator

import httpx

from server.adapters.stt.base import STTAdapter, TranscriptEvent


class HTTPSTTAdapter(STTAdapter):
    """Talks to a dockerized STT microservice (server/services/stt_service.py)."""

    def __init__(self, endpoint: str):
        self._endpoint = endpoint

    async def transcribe_stream(self, audio_chunk: bytes) -> AsyncIterator[TranscriptEvent]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self._endpoint}/transcribe", content=audio_chunk)
            response.raise_for_status()
            data = response.json()
        yield TranscriptEvent(text=data["text"], is_final=True)
