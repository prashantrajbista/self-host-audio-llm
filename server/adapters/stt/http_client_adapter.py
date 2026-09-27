from collections.abc import AsyncIterator

import httpx

from server.adapters.stt.base import STTAdapter, TranscriptEvent


class HTTPSTTAdapter(STTAdapter):
    """Talks to a dockerized STT microservice (server/services/stt_service.py)."""

    def __init__(self, endpoint: str):
        self._endpoint = endpoint

    async def transcribe_stream(self, audio_chunk: bytes) -> AsyncIterator[TranscriptEvent]:
        # ponytail: CPU whisper inference can run long on a modest server; generous read timeout,
        # tight connect timeout so a genuinely dead service still fails fast.
        timeout = httpx.Timeout(connect=5.0, read=180.0, write=30.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{self._endpoint}/transcribe", content=audio_chunk)
            response.raise_for_status()
            data = response.json()
        yield TranscriptEvent(text=data["text"], is_final=True)
