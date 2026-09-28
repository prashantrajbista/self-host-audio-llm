"""Phase 2 check: VoiceSession state machine + barge-in, with fake adapters (no models needed).
Run: python -m tests.test_session
"""

import asyncio

from server.adapters.llm.base import LLMAdapter
from server.adapters.stt.base import STTAdapter, TranscriptEvent
from server.adapters.tts.base import TTSAdapter
from server.gateway.session import VoiceSession, _split_speakable

SPEECH_FRAME = b"\x01" + b"\x00" * 639
SILENCE_FRAME = b"\x00" * 640


class FakeVAD:
    def is_speech(self, frame: bytes) -> bool:
        return frame[:1] == b"\x01"


class FakeSTT(STTAdapter):
    async def transcribe_stream(self, audio_chunk: bytes):
        yield TranscriptEvent(text="hello there", is_final=True)


class FakeLLM(LLMAdapter):
    def __init__(self):
        self.cancelled = False

    async def generate_stream(self, messages):
        for word in ["Hi", " there", "."]:
            if self.cancelled:
                return
            await asyncio.sleep(0.01)
            yield word

    async def cancel(self):
        self.cancelled = True


class FakeTTS(TTSAdapter):
    async def synthesize_stream(self, text_chunk: str):
        yield b"\x00\x01" * 10


async def main():
    events = []
    audio_chunks = []

    async def send_json(msg):
        events.append(msg)

    async def send_bytes(chunk):
        audio_chunks.append(chunk)

    session = VoiceSession(
        stt=FakeSTT(), llm=FakeLLM(), tts=FakeTTS(), vad=FakeVAD(),
        send_json=send_json, send_bytes=send_bytes,
    )

    # speech (past onset debounce threshold), then enough silence to trigger end-of-utterance
    for _ in range(8):
        await session.handle_audio_frame(SPEECH_FRAME)
    for _ in range(26):
        await session.handle_audio_frame(SILENCE_FRAME)

    await asyncio.sleep(0.2)  # let the turn task finish

    states = [e["data"] for e in events if e["type"] == "state"]
    assert "listening" in states, states
    assert "thinking" in states, states
    assert "speaking" in states, states
    assert "idle" in states, states
    assert any(e["type"] == "partial_transcript" for e in events), events
    assert audio_chunks, "no audio produced"
    print("state machine PASS:", states)

    # --- barge-in: speak again while session is speaking ---
    events.clear()
    audio_chunks.clear()
    session.state = "speaking"
    session._interrupt.clear()
    llm2 = session._llm
    for _ in range(8):
        await session.handle_audio_frame(SPEECH_FRAME)
    assert session._interrupt.is_set()
    assert llm2.cancelled
    assert any(e["type"] == "interrupt" for e in events), events
    print("barge-in PASS")

    # --- noise blip: a few speech frames below the debounce threshold should be ignored ---
    events.clear()
    session2 = VoiceSession(
        stt=FakeSTT(), llm=FakeLLM(), tts=FakeTTS(), vad=FakeVAD(),
        send_json=send_json, send_bytes=send_bytes,
    )
    for _ in range(3):  # below SPEECH_FRAMES_START_THRESHOLD (5)
        await session2.handle_audio_frame(SPEECH_FRAME)
    for _ in range(5):
        await session2.handle_audio_frame(SILENCE_FRAME)
    assert session2.state == "idle", session2.state
    assert not events, f"noise blip should not emit any events, got {events}"
    print("noise-blip rejection PASS")

    # --- barge-in while still thinking: must cancel the in-flight turn, not start a second one ---
    events.clear()
    session3 = VoiceSession(
        stt=FakeSTT(), llm=FakeLLM(), tts=FakeTTS(), vad=FakeVAD(),
        send_json=send_json, send_bytes=send_bytes,
    )
    session3.state = "thinking"
    session3._turn_task = asyncio.create_task(asyncio.sleep(10))
    for _ in range(8):
        await session3.handle_audio_frame(SPEECH_FRAME)
    await asyncio.sleep(0)
    assert session3._turn_task.cancelled()
    assert session3.state == "listening", session3.state
    print("barge-in during thinking PASS")

    # --- TTS chunking: split on sentence end + whitespace, first chunk may end at a clause ---
    assert _split_speakable("costs 3.5 dollars", False) is None
    assert _split_speakable("Hi there. How", False) == ("Hi there. ", "How")
    assert _split_speakable("Hi there!", False) is None  # no trailing space yet: wait for next token
    assert _split_speakable("Well, sure", True) is None  # too few words before the comma
    assert _split_speakable("Yes I can, sure", True) == ("Yes I can, ", "sure")
    assert _split_speakable("Yes I can, sure", False) is None  # clause split is first-chunk only
    print("chunk splitting PASS")


if __name__ == "__main__":
    asyncio.run(main())
