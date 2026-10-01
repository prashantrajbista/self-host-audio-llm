"""Phase 2 check: VoiceSession state machine + barge-in, with fake adapters (no models needed).
Run: python -m tests.test_session
"""

import asyncio

from server.adapters.llm.base import Done, LLMAdapter, TextDelta
from server.adapters.stt.base import STTAdapter, TranscriptEvent
from server.adapters.tts.base import TTSAdapter
from server.config import Settings, resolve_voice
from server.gateway.session import SPEECH_FRAMES_START_THRESHOLD, VoiceSession, _split_speakable

SPEECH_FRAME = b"\x01" + b"\x00" * 639
SILENCE_FRAME = b"\x00" * 640


class FakeVAD:
    def is_speech(self, frame: bytes) -> bool:
        return frame[:1] == b"\x01"


class FakeSTT(STTAdapter):
    async def transcribe_stream(self, audio_chunk: bytes):
        yield TranscriptEvent(text="hello there", is_final=True)


class FakeLLM(LLMAdapter):
    def __init__(self, delay=0.01):
        self.closed = False  # generator closed mid-stream = HTTP request aborted
        self.calls = 0
        self.delay = delay

    async def generate_stream(self, messages, tools=None, **params):
        self.calls += 1
        try:
            for word in ["Hi", " there", "."]:
                await asyncio.sleep(self.delay)
                yield TextDelta(word)
            yield Done("stop", None, "fake")
        except BaseException:
            self.closed = True
            raise


class FakeTTS(TTSAdapter):
    async def synthesize_stream(self, text_chunk: str, voice: str | None = None):
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
    for _ in range(8):
        await session.handle_audio_frame(SPEECH_FRAME)
    assert session._interrupt.is_set()
    assert any(e["type"] == "interrupt" for e in events), events
    print("barge-in PASS")

    # --- noise blip: a few speech frames below the debounce threshold should be ignored ---
    events.clear()
    session2 = VoiceSession(
        stt=FakeSTT(), llm=FakeLLM(), tts=FakeTTS(), vad=FakeVAD(),
        send_json=send_json, send_bytes=send_bytes,
    )
    for _ in range(SPEECH_FRAMES_START_THRESHOLD - 1):
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

    # --- client tap-to-interrupt: cancels the in-flight turn and returns to idle ---
    events.clear()
    session4 = VoiceSession(
        stt=FakeSTT(), llm=FakeLLM(), tts=FakeTTS(), vad=FakeVAD(),
        send_json=send_json, send_bytes=send_bytes,
    )
    session4.state = "speaking"
    session4._turn_task = asyncio.create_task(asyncio.sleep(10))
    await session4.interrupt()
    await asyncio.sleep(0)
    assert session4._turn_task.cancelled()
    assert session4.state == "idle", session4.state
    session4.state = "idle"
    events.clear()
    await session4.interrupt()  # nothing in flight: no-op
    assert not events, events
    print("client interrupt PASS")

    # --- TTS chunking: split on sentence end + whitespace, first chunk may end at a clause ---
    assert _split_speakable("costs 3.5 dollars", False) is None
    assert _split_speakable("Hi there. How", False) == ("Hi there. ", "How")
    assert _split_speakable("Hi there!", False) is None  # no trailing space yet: wait for next token
    assert _split_speakable("Well, sure", True) is None  # too few words before the comma
    assert _split_speakable("Yes I can, sure", True) == ("Yes I can, ", "sure")
    assert _split_speakable("Yes I can, sure", False) is None  # clause split is first-chunk only
    print("chunk splitting PASS")

    # --- speculative LLM: started at ~200ms of silence and reused by the turn, not requested twice ---
    events.clear()
    llm5 = FakeLLM()
    session5 = VoiceSession(stt=FakeSTT(), llm=llm5, tts=FakeTTS(), vad=FakeVAD(), send_json=send_json, send_bytes=send_bytes)
    for _ in range(8):
        await session5.handle_audio_frame(SPEECH_FRAME)
    for _ in range(26):
        await session5.handle_audio_frame(SILENCE_FRAME)
        await asyncio.sleep(0)
    await asyncio.sleep(0.2)
    assert llm5.calls == 1, llm5.calls
    trace = next(e["data"] for e in events if e["type"] == "trace")
    assert trace["prefetched"], trace
    print("speculative LLM reuse PASS")

    # --- speech resumes after the speculative point: prefetched request is aborted ---
    llm6 = FakeLLM(delay=0.2)
    session6 = VoiceSession(stt=FakeSTT(), llm=llm6, tts=FakeTTS(), vad=FakeVAD(), send_json=send_json, send_bytes=send_bytes)
    for _ in range(8):
        await session6.handle_audio_frame(SPEECH_FRAME)
    for _ in range(12):  # past the speculative point, short of end of turn
        await session6.handle_audio_frame(SILENCE_FRAME)
    await asyncio.sleep(0.05)  # prefetch request is in flight
    assert llm6.calls == 1
    await session6.handle_audio_frame(SPEECH_FRAME)
    await asyncio.sleep(0.05)
    assert llm6.closed, "resumed speech must abort the speculative request"
    session6.close()
    print("speculative LLM cancel PASS")

    # --- session cap: past MAX_SESSIONS the call is refused with 1013, not admitted ---
    from server.gateway import ws_handler

    class FakeWS:
        client = None
        query_params: dict = {}
        closed_with = None

        async def accept(self):
            pass

        async def close(self, code=1000, reason=""):
            self.closed_with = code

    ws_handler._active_sessions = ws_handler.get_settings().max_sessions
    ws = FakeWS()
    await ws_handler.websocket_endpoint(ws)
    assert ws.closed_with == ws_handler.BUSY_CLOSE_CODE, ws.closed_with
    ws_handler._active_sessions = 0
    print("session cap PASS")

    # --- voice selection: allowed voices pass through, anything else falls back to the default ---
    settings = Settings(tts_voice="af_heart", tts_voices=["af_heart", "am_michael"])
    assert resolve_voice(settings, "am_michael") == "am_michael"
    assert resolve_voice(settings, "../../etc/passwd") == "af_heart"
    assert resolve_voice(settings, None) == "af_heart"
    print("voice resolution PASS")


if __name__ == "__main__":
    asyncio.run(main())
