import asyncio
from collections.abc import Awaitable, Callable

from server.adapters.llm.base import LLMAdapter, Message
from server.adapters.stt.base import STTAdapter
from server.adapters.tts.base import TTSAdapter
from server.vad.vad import VAD

FRAME_MS = 20
SILENCE_FRAMES_END_OF_TURN = 25  # ~500ms of trailing silence ends the utterance
SENTENCE_ENDERS = (".", "!", "?")


class VoiceSession:
    """Per-connection state machine: idle -> listening -> thinking -> speaking, with barge-in."""

    def __init__(
        self,
        stt: STTAdapter,
        llm: LLMAdapter,
        tts: TTSAdapter,
        vad: VAD,
        send_json: Callable[[dict], Awaitable[None]],
        send_bytes: Callable[[bytes], Awaitable[None]],
    ):
        self._stt = stt
        self._llm = llm
        self._tts = tts
        self._vad = vad
        self._send_json = send_json
        self._send_bytes = send_bytes

        self.state = "idle"
        self._audio_buffer = bytearray()
        self._speech_started = False
        self._silence_frames = 0
        self._interrupt = asyncio.Event()
        self._turn_task: asyncio.Task | None = None

    async def handle_audio_frame(self, frame: bytes) -> None:
        is_speech = self._vad.is_speech(frame)

        if self.state == "speaking" and is_speech:
            await self._barge_in()

        if is_speech:
            self._audio_buffer.extend(frame)
            self._silence_frames = 0
            if not self._speech_started:
                self._speech_started = True
                await self._set_state("listening")
        elif self._speech_started:
            self._audio_buffer.extend(frame)
            self._silence_frames += 1
            if self._silence_frames >= SILENCE_FRAMES_END_OF_TURN:
                await self._end_of_utterance()

    async def _end_of_utterance(self) -> None:
        audio = bytes(self._audio_buffer)
        self._audio_buffer.clear()
        self._speech_started = False
        self._silence_frames = 0
        self._interrupt.clear()
        await self._set_state("thinking")
        self._turn_task = asyncio.create_task(self._process_turn(audio))

    async def _process_turn(self, audio: bytes) -> None:
        try:
            transcript = ""
            async for event in self._stt.transcribe_stream(audio):
                if event.is_final:
                    transcript = event.text
            if not transcript.strip() or self._interrupt.is_set():
                await self._set_state("idle")
                return
            await self._send_json({"type": "partial_transcript", "data": transcript})

            await self._set_state("speaking")
            sentence_buf = ""
            async for token in self._llm.generate_stream([Message(role="user", content=transcript)]):
                if self._interrupt.is_set():
                    break
                await self._send_json({"type": "token", "data": token})
                sentence_buf += token
                if sentence_buf.rstrip().endswith(SENTENCE_ENDERS):
                    await self._speak(sentence_buf)
                    sentence_buf = ""
            if sentence_buf.strip() and not self._interrupt.is_set():
                await self._speak(sentence_buf)

            if not self._interrupt.is_set():
                await self._set_state("idle")
        except asyncio.CancelledError:
            pass

    async def _speak(self, text: str) -> None:
        async for chunk in self._tts.synthesize_stream(text):
            if self._interrupt.is_set():
                break
            await self._send_bytes(chunk)

    async def _barge_in(self) -> None:
        self._interrupt.set()
        await self._llm.cancel()
        if self._turn_task:
            self._turn_task.cancel()
        await self._send_json({"type": "interrupt"})
        self._audio_buffer.clear()
        self._speech_started = True
        self._silence_frames = 0
        await self._set_state("listening")

    async def _set_state(self, state: str) -> None:
        self.state = state
        await self._send_json({"type": "state", "data": state})
