"""Phase 1 check: one full turn through STT -> LLM -> TTS. Run: python -m tests.test_turn <wav_path>"""

import asyncio
import sys

from server.config import get_settings
from server.gateway.factory import get_llm, get_stt, get_tts
from server.gateway.orchestrator import Orchestrator


async def main(wav_path: str):
    settings = get_settings()
    orchestrator = Orchestrator(
        stt=get_stt(settings),
        llm=get_llm(settings),
        tts=get_tts(settings),
    )
    with open(wav_path, "rb") as f:
        audio = f.read()

    transcript, reply_text, audio_out = await orchestrator.run_turn(audio)

    assert transcript, "STT produced no transcript"
    assert reply_text, "LLM produced no reply"
    assert audio_out, "TTS produced no audio"

    print(f"transcript: {transcript!r}")
    print(f"reply_text: {reply_text!r}")
    print(f"audio_out bytes: {len(audio_out)}")
    print("PASS")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/test_sample.wav"))
