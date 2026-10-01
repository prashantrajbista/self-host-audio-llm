import io
import wave
from collections.abc import AsyncIterator

from server.adapters.http_client import shared_client
from server.adapters.stt.base import STTAdapter, TranscriptEvent


def to_wav(pcm16: bytes, rate: int = 16000) -> bytes:
    """Raw mono PCM16 (the WS mic stream) as a WAV file; WAV input passes through."""
    if pcm16[:4] == b"RIFF":
        return pcm16
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm16)
    return buf.getvalue()


AZURE_API_VERSION = "2025-03-01-preview"  # first version with the gpt-4o(-mini)-transcribe models


class OpenAISTTAdapter(STTAdapter):
    """OpenAI-compatible /v1/audio/transcriptions: OpenAI, or Azure OpenAI / Foundry (endpoint .../openai,
    model = deployment name). One request per finished utterance; the gateway's VAD decides when that is."""

    def __init__(self, endpoint: str, model: str, api_key: str):
        base = endpoint.rstrip("/")
        # Azure's /openai/v1 route doesn't resolve transcription deployments (DeploymentNotFound); its
        # per-deployment route does
        if ".azure.com" in base:
            self._url = f"{base}/deployments/{model}/audio/transcriptions?api-version={AZURE_API_VERSION}"
        else:
            self._url = f"{base}/v1/audio/transcriptions"
        self._model = model
        self._headers = {"Authorization": f"Bearer {api_key}", "api-key": api_key}

    async def transcribe_stream(self, audio_chunk: bytes) -> AsyncIterator[TranscriptEvent]:
        response = await shared_client().post(
            self._url,
            headers=self._headers,
            files={"file": ("utterance.wav", to_wav(audio_chunk), "audio/wav")},
            data={"model": self._model, "language": "en", "response_format": "json"},
        )
        if response.status_code >= 400:
            raise RuntimeError(f"STT HTTP {response.status_code}: {response.text[:500]}")
        yield TranscriptEvent(text=response.json()["text"].strip(), is_final=True)
