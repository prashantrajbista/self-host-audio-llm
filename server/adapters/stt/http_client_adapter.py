from collections.abc import AsyncIterator

from server.adapters.http_client import shared_client
from server.adapters.stt.base import STTAdapter, TranscriptEvent


class HTTPSTTAdapter(STTAdapter):
    """Talks to a dockerized STT microservice (server/services/stt_service.py)."""

    def __init__(self, endpoint: str):
        self._endpoint = endpoint

    async def transcribe_stream(self, audio_chunk: bytes) -> AsyncIterator[TranscriptEvent]:
        response = await shared_client().post(f"{self._endpoint}/transcribe", content=audio_chunk)
        response.raise_for_status()
        data = response.json()
        yield TranscriptEvent(text=data["text"], is_final=True)
