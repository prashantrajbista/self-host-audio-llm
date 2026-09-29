"""Phase 1 check: one full turn through STT -> LLM -> TTS via VoiceSession, with the real backends
.env selects (VAD bypassed — the whole WAV is one utterance). Run: python -m tests.test_turn <wav_path>
"""

import asyncio
import sys

from server.config import get_settings
from server.gateway.factory import get_llm, get_stt, get_tts
from server.gateway.session import VoiceSession


async def main(wav_path: str):
    settings = get_settings()
    events = []
    audio_out = bytearray()

    async def send_json(msg):
        events.append(msg)

    async def send_bytes(chunk):
        audio_out.extend(chunk)

    session = VoiceSession(
        stt=get_stt(settings), llm=get_llm(settings), tts=get_tts(settings), vad=None,
        send_json=send_json, send_bytes=send_bytes,
    )
    with open(wav_path, "rb") as f:
        audio = f.read()

    await session._process_turn(asyncio.create_task(session._speculate(audio, prefetch=False)))

    transcript = "".join(e["data"] for e in events if e["type"] == "partial_transcript")
    reply_text = "".join(e["data"] for e in events if e["type"] == "token")
    assert transcript, "STT produced no transcript"
    assert reply_text, "LLM produced no reply"
    assert audio_out, "TTS produced no audio"

    print(f"transcript: {transcript!r}")
    print(f"reply_text: {reply_text!r}")
    print(f"audio_out bytes: {len(audio_out)}")
    print("PASS")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/test_sample.wav"))
