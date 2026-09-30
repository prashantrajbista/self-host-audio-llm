"""Check: the ONNX Kokoro adapter produces PCM16 audio for every selectable voice.
Needs the model files (see TTS_ONNX_MODEL / TTS_ONNX_VOICES). Run: python -m tests.test_tts_onnx
"""

import asyncio

from server.adapters.tts.kokoro_onnx_adapter import KokoroOnnxAdapter
from server.config import get_settings


async def main() -> None:
    settings = get_settings()
    adapter = KokoroOnnxAdapter(settings.tts_onnx_model, settings.tts_onnx_voices, speed=settings.tts_speed, threads=2)
    for voice in settings.tts_voices:
        pcm = b"".join([chunk async for chunk in adapter.synthesize_stream("Hello there.", voice=voice)])
        assert len(pcm) > 24000 * 2 * 0.3 and len(pcm) % 2 == 0, f"{voice}: {len(pcm)} bytes"
    print(f"kokoro onnx PASS ({len(settings.tts_voices)} voices)")


if __name__ == "__main__":
    asyncio.run(main())
