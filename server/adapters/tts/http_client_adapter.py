from collections.abc import AsyncIterator

import httpx

from server.adapters.tts.base import TTSAdapter


class HTTPTTSAdapter(TTSAdapter):
    """Talks to a dockerized TTS microservice (server/services/tts_service.py)."""

    def __init__(self, endpoint: str):
        self._endpoint = endpoint

    async def synthesize_stream(self, text_chunk: str) -> AsyncIterator[bytes]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{self._endpoint}/synthesize", json={"text": text_chunk}) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk
