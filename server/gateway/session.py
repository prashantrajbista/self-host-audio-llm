import asyncio
import logging
import re
import time
import wave
from collections import deque
from pathlib import Path
from collections.abc import Awaitable, Callable

from server.adapters.llm.base import LLMAdapter, Message
from server.adapters.stt.base import STTAdapter
from server.adapters.tts.base import TTSAdapter
from server.vad.vad import VAD

logger = logging.getLogger(__name__)

FRAME_MS = 20
SILENCE_FRAMES_END_OF_TURN = 25  # ~500ms of trailing silence ends the utterance
# ~200ms of silence: start transcribing speculatively, so STT overlaps the rest of the end-of-turn
# wait. Speech resuming cancels it; if silence holds, the turn reuses the result (the audio after
# the snapshot is only silence, which wouldn't change the transcript).
SILENCE_FRAMES_SPECULATIVE_STT = 10
SPEECH_FRAMES_START_THRESHOLD = 3  # ~60ms of consecutive speech before committing — filters noise blips
PREROLL_FRAMES = 15  # ~300ms kept from before speech was detected, so soft onsets ("h" in "hi") aren't clipped
LLM_FIRST_TOKEN_TIMEOUT = 15.0  # s; a hung request would otherwise leave the session stuck in "thinking"
LLM_RETRIES = 1  # retried only before the first token, so a partial reply is never repeated
FALLBACK_LINE = "Sorry, I had trouble with that. Could you say it again?"
# Whisper's classic outputs on noise-only audio; "thank you" alone is left out because users do say it
_STT_HALLUCINATIONS = {"you", "thanks for watching", "thank you for watching"}
FIRST_CHUNK_MIN_WORDS = 3  # the first TTS chunk may end at a comma once it has this many words
# Everything the model writes is spoken aloud by TTS, so ask for speakable text up front rather than
# relying only on _strip_markdown after the fact (which remains as a safety net).
SYSTEM_PROMPT = (
    "You are a friendly voice assistant in a live spoken conversation. Everything you write is read aloud "
    "by a text-to-speech engine, so write only what should be spoken.\n"
    "- Keep answers short: a sentence or two unless the user asks for more detail.\n"
    "- Talk like a person: plain conversational sentences, contractions, no filler.\n"
    "- Never use markdown, bullet points, numbered lists, headings, tables, code blocks, emojis, or URLs. "
    "If you need to list things, say them in a sentence, like \"first..., then..., and finally...\".\n"
    "- Write numbers, dates, times, units, and symbols the way they're said: \"twenty-five degrees\", "
    "\"three thirty pm\", \"about five percent\", \"forty dollars\".\n"
    "- Spell out abbreviations that aren't normally said as letters, and avoid parentheses.\n"
    "- The user's words come from speech-to-text and may contain mishearings. If a message seems oddly worded or "
    "out of context, ask what they meant instead of guessing.\n"
    "- If the request is unclear or you didn't catch it, briefly ask the user to repeat or clarify."
)

_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_HEADING = re.compile(r"^#{1,6}\s*", re.MULTILINE)
_MD_LIST_BULLET = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
_MD_EMPHASIS = re.compile(r"[*_`~]+")
_WHITESPACE = re.compile(r"\s+")
# sentence end = terminal punctuation followed by whitespace, so "3.5" or "e.g" mid-token doesn't split
_SENTENCE_END = re.compile(r"[.!?]+[\"')\]]*\s")
_CLAUSE_END = re.compile(r"[,;:]\s")


def _split_speakable(buf: str, first: bool) -> tuple[str, str] | None:
    """Return (chunk_to_speak, remainder) once buf holds a speakable unit, else None. The first
    chunk of a reply may also end at a clause boundary, so audio starts before a full sentence."""
    m = _SENTENCE_END.search(buf)
    if m:
        return buf[: m.end()], buf[m.end() :]
    if first:
        for m in _CLAUSE_END.finditer(buf):
            if len(buf[: m.end()].split()) >= FIRST_CHUNK_MIN_WORDS:
                return buf[: m.end()], buf[m.end() :]
    return None


def _is_usable_transcript(text: str) -> bool:
    """False for empty/punctuation-only text and Whisper's known noise hallucinations."""
    words = re.sub(r"[^\w\s']", "", text).lower().split()
    return bool(words) and " ".join(words) not in _STT_HALLUCINATIONS


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
        voice: str | None = None,
    ):
        self._stt = stt
        self._llm = llm
        self._tts = tts
        self._voice = voice
        self._vad = vad
        self._send_json = send_json
        self._send_bytes = send_bytes

        self.state = "idle"
        self._audio_buffer = bytearray()
        self._speech_started = False
        self._silence_frames = 0
        self._pending_frames: list[bytes] = []
        self._preroll: deque[bytes] = deque(maxlen=PREROLL_FRAMES)
        self._interrupt = asyncio.Event()
        self._turn_task: asyncio.Task | None = None
        self._stt_task: asyncio.Task | None = None  # speculative transcription of the current utterance

    async def handle_audio_frame(self, frame: bytes) -> None:
        is_speech = self._vad.is_speech(frame)

        if not self._speech_started:
            self._preroll.append(frame)
            # debounce onset: require several consecutive speech frames before committing,
            # so a single noisy/misclassified frame doesn't start a turn or trigger barge-in
            if not is_speech:
                self._pending_frames.clear()
                return
            self._pending_frames.append(frame)
            if len(self._pending_frames) < SPEECH_FRAMES_START_THRESHOLD:
                return
            # a turn is in flight (still transcribing/generating, or already speaking): new speech
            # replaces it — otherwise a second turn would start alongside the first and both reply
            if self.state in ("thinking", "speaking"):
                await self._barge_in()
            else:
                self._speech_started = True
                await self._set_state("listening")
            # preroll already holds the pending frames plus the audio just before them
            self._audio_buffer.extend(b"".join(self._preroll))
            self._preroll.clear()
            self._pending_frames.clear()
            self._silence_frames = 0
            return

        self._audio_buffer.extend(frame)
        if is_speech:
            self._silence_frames = 0
            self._cancel_speculative_stt()
        else:
            self._silence_frames += 1
            if self._silence_frames == SILENCE_FRAMES_SPECULATIVE_STT:
                self._stt_task = asyncio.create_task(self._transcribe(bytes(self._audio_buffer)))
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
        # TEMP debug: save what STT receives so recording quality can be listened to (audios/ is gitignored)
        Path("audios").mkdir(exist_ok=True)
        with wave.open(f"audios/utt_{time.strftime('%H%M%S')}_{time.time_ns() % 1000}.wav", "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(audio)
        stt_task = self._stt_task or asyncio.create_task(self._transcribe(audio))
        self._stt_task = None
        await self._set_state("thinking")
        self._turn_task = asyncio.create_task(self._process_turn(stt_task))

    async def _transcribe(self, audio: bytes) -> str:
        transcript = ""
        async for event in self._stt.transcribe_stream(audio):
            if event.is_final:
                transcript = event.text
        return transcript

    def _cancel_speculative_stt(self) -> None:
        if self._stt_task:
            # retrieve any exception so a failed-then-discarded task doesn't log "never retrieved"
            self._stt_task.add_done_callback(lambda t: t.cancelled() or t.exception())
            self._stt_task.cancel()
            self._stt_task = None

    async def _process_turn(self, stt_task: asyncio.Task) -> None:
        speaker: asyncio.Task | None = None
        try:
            transcript = await stt_task
            logger.info("transcript: %r", transcript)
            if not _is_usable_transcript(transcript) or self._interrupt.is_set():
                await self._set_state("idle")
                return
            await self._send_json({"type": "partial_transcript", "data": transcript})

            await self._set_state("speaking")
            # LLM and TTS run concurrently: generation keeps streaming into the queue while earlier
            # chunks are being synthesized, instead of stalling for each chunk's synthesis
            queue: asyncio.Queue[str | None] = asyncio.Queue()
            speaker = asyncio.create_task(self._speaker(queue))
            buf = ""
            reply = ""
            first = True
            messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=transcript)]
            async for token in self._stream_llm(messages):
                if self._interrupt.is_set():
                    break
                await self._send_json({"type": "token", "data": token})
                buf += token
                reply += token
                while split := _split_speakable(buf, first):
                    chunk, buf = split
                    queue.put_nowait(chunk)
                    first = False
            if buf.strip() and not self._interrupt.is_set():
                queue.put_nowait(buf)
            queue.put_nowait(None)
            await speaker
            logger.info("reply: %r", reply)

            if not self._interrupt.is_set():
                await self._set_state("idle")
        except asyncio.CancelledError:
            logger.debug("turn cancelled (barge-in)")
        except Exception:
            logger.exception("turn failed")
            if speaker:
                speaker.cancel()
            await self._send_json({"type": "error", "data": FALLBACK_LINE})
            try:
                await self._speak(FALLBACK_LINE)
            except Exception:
                logger.exception("fallback speech failed")
            await self._set_state("idle")
        finally:
            if speaker:
                speaker.cancel()

    async def _stream_llm(self, messages: list[Message]):
        """LLM tokens with a first-token timeout and retry; retrying is only safe before anything was yielded."""
        for attempt in range(LLM_RETRIES + 1):
            gen = self._llm.generate_stream(messages)
            got_token = False
            try:
                while True:
                    token = await asyncio.wait_for(anext(gen), None if got_token else LLM_FIRST_TOKEN_TIMEOUT)
                    got_token = True
                    yield token
            except StopAsyncIteration:
                return
            except Exception:
                if got_token or attempt == LLM_RETRIES:
                    raise
                logger.warning("llm failed before first token, retrying", exc_info=True)
            finally:
                await gen.aclose()

    async def _speaker(self, queue: "asyncio.Queue[str | None]") -> None:
        while (text := await queue.get()) is not None:
            await self._speak(text)

    async def _speak(self, text: str) -> None:
        text = _strip_markdown(text)
        if not text.strip():
            return
        async for chunk in self._tts.synthesize_stream(text, voice=self._voice):
            if self._interrupt.is_set():
                break
            await self._send_bytes(chunk)

    async def _stop_turn(self) -> None:
        """Cancel whatever turn is in flight: LLM stream, turn task (and its TTS), speculative STT."""
        self._interrupt.set()
        await self._llm.cancel()
        if self._turn_task:
            self._turn_task.cancel()
        self._cancel_speculative_stt()

    async def _barge_in(self) -> None:
        logger.info("barge-in detected")
        await self._stop_turn()
        await self._send_json({"type": "interrupt"})
        self._audio_buffer.clear()
        self._speech_started = True
        self._silence_frames = 0
        await self._set_state("listening")

    async def interrupt(self) -> None:
        """Client-initiated stop (tap on the orb): drop the current reply and wait for new speech.
        No-op when nothing is in flight. The client already stopped its own playback."""
        if self.state not in ("thinking", "speaking"):
            return
        logger.info("client interrupt")
        await self._stop_turn()
        self._audio_buffer.clear()
        self._pending_frames.clear()
        self._speech_started = False
        self._silence_frames = 0
        await self._set_state("idle")

    def close(self) -> None:
        """Connection gone: stop in-flight work so it doesn't keep running and sending to a dead socket."""
        if self._turn_task:
            self._turn_task.cancel()
        self._cancel_speculative_stt()

    async def _set_state(self, state: str) -> None:
        logger.debug("state: %s -> %s", self.state, state)
        self.state = state
        await self._send_json({"type": "state", "data": state})
