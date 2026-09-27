from collections.abc import AsyncIterator

import httpx

from server.adapters.tts.base import TTSAdapter


class HTTPTTSAdapter(TTSAdapter):
    """Talks to a dockerized TTS microservice (server/services/tts_service.py)."""

    def __init__(self, endpoint: str):
        self._endpoint = endpoint

    async def synthesize_stream(self, text_chunk: str) -> AsyncIterator[bytes]:
        timeout = httpx.Timeout(connect=5.0, read=180.0, write=30.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", f"{self._endpoint}/synthesize", json={"text": text_chunk}) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk
