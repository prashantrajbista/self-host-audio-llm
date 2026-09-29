from collections.abc import AsyncIterator

from server.adapters.http_client import shared_client
from server.adapters.tts.base import TTSAdapter


class HTTPTTSAdapter(TTSAdapter):
    """Talks to a dockerized TTS microservice (server/services/tts_service.py)."""

    def __init__(self, endpoint: str):
        self._endpoint = endpoint

    async def synthesize_stream(self, text_chunk: str, voice: str | None = None) -> AsyncIterator[bytes]:
        async with shared_client().stream(
            "POST", f"{self._endpoint}/synthesize", json={"text": text_chunk, "voice": voice}
        ) as response:
            response.raise_for_status()
            # network chunks can end mid-sample; the client reads int16, so only whole samples go out
            carry = b""
            async for chunk in response.aiter_bytes():
                data = carry + chunk
                whole = len(data) & ~1
                carry = data[whole:]
                if whole:
                    yield data[:whole]
