"""OpenAI-compatible STT/TTS adapters (OpenAI, Azure OpenAI / Foundry) against a mock HTTP transport, no network.
Run: python -m tests.test_openai_audio
"""

import asyncio
import io
import json
import wave

import httpx

from server.adapters import http_client
from server.adapters.stt.openai_adapter import OpenAISTTAdapter
from server.adapters.tts.openai_adapter import OpenAITTSAdapter

ENDPOINT = "https://res.openai.azure.com/openai"
PCM = b"\x01\x02" * 1600  # 0.1s of 16kHz mono PCM16


def handler(request: httpx.Request) -> httpx.Response:
    assert request.headers["api-key"] == "k" and request.headers["authorization"] == "Bearer k"
    if request.url.path == "/openai/deployments/gpt-4o-mini-transcribe/audio/transcriptions":
        assert request.url.params["api-version"], request.url
        body = request.read()
        assert b'name="model"\r\n\r\ngpt-4o-mini-transcribe' in body, body[:300]
        wav = body[body.index(b"RIFF") :]
        with wave.open(io.BytesIO(wav)) as w:
            assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)
            assert w.readframes(w.getnframes()) == PCM
        return httpx.Response(200, json={"text": " Hello there. "})
    if request.url.path == "/openai/v1/audio/speech":
        payload = json.loads(request.read())
        assert payload["response_format"] == "pcm" and payload["model"] == "gpt-4o-mini-tts", payload
        assert payload["voice"] == "ash", payload  # Kokoro id mapped
        # odd-sized network chunks: the adapter must only yield whole int16 samples
        return httpx.Response(200, content=_chunks(b"\x00" * 3, b"\x00" * 4, b"\x00"))
    return httpx.Response(404)


async def _chunks(*parts: bytes):
    for p in parts:
        yield p


async def main():
    http_client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    stt = OpenAISTTAdapter(ENDPOINT, "gpt-4o-mini-transcribe", "k")
    events = [e async for e in stt.transcribe_stream(PCM)]
    assert [e.text for e in events] == ["Hello there."], events
    print("STT PASS")

    tts = OpenAITTSAdapter(ENDPOINT, "gpt-4o-mini-tts", "k", voice="af_heart")
    chunks = [c async for c in tts.synthesize_stream("Hi.", voice="am_michael")]
    assert all(len(c) % 2 == 0 for c in chunks) and sum(map(len, chunks)) == 8, [len(c) for c in chunks]
    print("TTS PASS")


if __name__ == "__main__":
    asyncio.run(main())
