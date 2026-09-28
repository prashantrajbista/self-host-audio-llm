import asyncio
import logging
import re
from collections.abc import Awaitable, Callable

from server.adapters.llm.base import LLMAdapter, Message
from server.adapters.stt.base import STTAdapter
from server.adapters.tts.base import TTSAdapter
from server.vad.vad import VAD

logger = logging.getLogger(__name__)

FRAME_MS = 20
SILENCE_FRAMES_END_OF_TURN = 25  # ~500ms of trailing silence ends the utterance
SPEECH_FRAMES_START_THRESHOLD = 5  # ~100ms of consecutive speech before committing — filters noise blips
SENTENCE_ENDERS = (".", "!", "?")
SYSTEM_PROMPT = "You are a voice assistant. Keep answers short — a sentence or two unless the user asks for more detail."

_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_HEADING = re.compile(r"^#{1,6}\s*", re.MULTILINE)
_MD_LIST_BULLET = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
_MD_EMPHASIS = re.compile(r"[*_`~]+")
_WHITESPACE = re.compile(r"\s+")


def _strip_markdown(text: str) -> str:
    """Drop markdown syntax the LLM emits (#, **, _, `, - bullets, [links](url)) before it
    reaches TTS — spoken aloud literally, it reads as noise rather than the formatting it's
    meant to convey. The client still gets the raw token stream for on-screen rendering."""
    text = _MD_LINK.sub(r"\1", text)
    text = _MD_HEADING.sub("", text)
    text = _MD_LIST_BULLET.sub("", text)
    text = _MD_EMPHASIS.sub("", text)
    # collapse after the ^-anchored substitutions above, which rely on real newlines —
    # Kokoro produces glitchy audio on literal \n mid-utterance, so it can't reach TTS raw
    text = _WHITESPACE.sub(" ", text).strip()
    return text


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
        self._pending_frames: list[bytes] = []
        self._interrupt = asyncio.Event()
        self._turn_task: asyncio.Task | None = None

    async def handle_audio_frame(self, frame: bytes) -> None:
        is_speech = self._vad.is_speech(frame)

        if not self._speech_started:
            # debounce onset: require several consecutive speech frames before committing,
            # so a single noisy/misclassified frame doesn't start a turn or trigger barge-in
            if not is_speech:
                self._pending_frames.clear()
                return
            self._pending_frames.append(frame)
            if len(self._pending_frames) < SPEECH_FRAMES_START_THRESHOLD:
                return
            if self.state == "speaking":
                await self._barge_in()
            else:
                self._speech_started = True
                await self._set_state("listening")
            self._audio_buffer.extend(b"".join(self._pending_frames))
            self._pending_frames.clear()
            self._silence_frames = 0
            return

        self._audio_buffer.extend(frame)
        if is_speech:
            self._silence_frames = 0
        else:
            self._silence_frames += 1
            if self._silence_frames >= SILENCE_FRAMES_END_OF_TURN:
                await self._end_of_utterance()

    async def _end_of_utterance(self) -> None:
        audio = bytes(self._audio_buffer)
        self._audio_buffer.clear()
        self._speech_started = False
        self._silence_frames = 0
        self._pending_frames.clear()
        self._interrupt.clear()
        logger.debug("end of utterance: %d bytes of audio", len(audio))
        await self._set_state("thinking")
        self._turn_task = asyncio.create_task(self._process_turn(audio))

    async def _process_turn(self, audio: bytes) -> None:
        try:
            transcript = ""
            async for event in self._stt.transcribe_stream(audio):
                if event.is_final:
                    transcript = event.text
            logger.info("transcript: %r", transcript)
            if not transcript.strip() or self._interrupt.is_set():
                await self._set_state("idle")
                return
            await self._send_json({"type": "partial_transcript", "data": transcript})

            await self._set_state("speaking")
            sentence_buf = ""
            reply = ""
            messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=transcript)]
            async for token in self._llm.generate_stream(messages):
                if self._interrupt.is_set():
                    break
                await self._send_json({"type": "token", "data": token})
                sentence_buf += token
                reply += token
                if sentence_buf.rstrip().endswith(SENTENCE_ENDERS):
                    await self._speak(sentence_buf)
                    sentence_buf = ""
            if sentence_buf.strip() and not self._interrupt.is_set():
                await self._speak(sentence_buf)
            logger.info("reply: %r", reply)

            if not self._interrupt.is_set():
                await self._set_state("idle")
        except asyncio.CancelledError:
            logger.debug("turn cancelled (barge-in)")
        except Exception:
            logger.exception("turn failed")
            await self._set_state("idle")

    async def _speak(self, text: str) -> None:
        text = _strip_markdown(text)
        if not text.strip():
            return
        async for chunk in self._tts.synthesize_stream(text):
            if self._interrupt.is_set():
                break
            await self._send_bytes(chunk)

    async def _barge_in(self) -> None:
        logger.info("barge-in detected")
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
        logger.debug("state: %s -> %s", self.state, state)
        self.state = state
        await self._send_json({"type": "state", "data": state})
