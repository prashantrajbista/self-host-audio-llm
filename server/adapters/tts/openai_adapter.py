from collections.abc import AsyncIterator

from server.adapters.http_client import shared_client
from server.adapters.tts.base import TTSAdapter

# The app's voice ids are Kokoro's (packs, client voice picker, previews); map them to the closest OpenAI voice.
# Anything else is passed through, so OpenAI voice names work directly too.
VOICE_MAP = {"am_michael": "ash", "af_heart": "coral", "af_bella": "shimmer", "am_fenrir": "onyx"}


class OpenAITTSAdapter(TTSAdapter):
    """OpenAI-compatible /v1/audio/speech: OpenAI, or Azure OpenAI / Foundry (endpoint .../openai, model =
    deployment name). Asks for raw PCM16 @ 24kHz, which is exactly what the client plays."""

    def __init__(self, endpoint: str, model: str, api_key: str, voice: str, instructions: str = ""):
        self._url = f"{endpoint.rstrip('/')}/v1/audio/speech"
        self._model = model
        self._headers = {"Authorization": f"Bearer {api_key}", "api-key": api_key}
        self._voice = voice
        self._instructions = instructions

    async def synthesize_stream(self, text_chunk: str, voice: str | None = None) -> AsyncIterator[bytes]:
        voice = voice or self._voice
        payload = {"model": self._model, "input": text_chunk, "voice": VOICE_MAP.get(voice, voice), "response_format": "pcm"}
        if self._instructions:
            payload["instructions"] = self._instructions
        async with shared_client().stream("POST", self._url, headers=self._headers, json=payload) as response:
            if response.status_code >= 400:
                body = (await response.aread()).decode(errors="replace")[:500]
                raise RuntimeError(f"TTS HTTP {response.status_code}: {body}")
            # network chunks can end mid-sample; the client reads int16, so only whole samples go out
            carry = b""
            async for chunk in response.aiter_bytes():
                data = carry + chunk
                whole = len(data) & ~1
                carry = data[whole:]
                if whole:
                    yield data[:whole]
