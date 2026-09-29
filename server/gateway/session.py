import asyncio
import json
import logging
import re
import time
from collections import deque
from collections.abc import Awaitable, Callable
from contextlib import aclosing
from dataclasses import asdict

from server.adapters.llm.base import LLMAdapter
from server.agent.agents import AGENTS, AgentDef
from server.agent.conversation import Conversation
from server.agent.loop import Filler, Prefetch, Speak, ToolFinished, ToolStarted, TurnTrace, run_turn
from server.adapters.stt.base import STTAdapter
from server.adapters.tts.base import TTSAdapter
from server.vad.vad import VAD

logger = logging.getLogger(__name__)

FRAME_MS = 20
SILENCE_FRAMES_END_OF_TURN = 25  # ~500ms of trailing silence ends the utterance
# ~200ms of silence: start transcribing speculatively, then start the first LLM request on that
# transcript, so STT and the LLM's time to first token overlap the rest of the end-of-turn wait.
# Speech resuming cancels both; if silence holds, the turn reuses them (the audio after the snapshot
# is only silence, which wouldn't change the transcript).
SILENCE_FRAMES_SPECULATIVE_STT = 10
SPEECH_FRAMES_START_THRESHOLD = 3  # ~60ms of consecutive speech before committing — filters noise blips
PREROLL_FRAMES = 15  # ~300ms kept from before speech was detected, so soft onsets ("h" in "hi") aren't clipped
TTS_BYTES_PER_SEC = 24000 * 2  # PCM16 @ 24kHz, what the client Player plays back
TTS_MAX_LEAD_S = 3.0  # don't send audio more than this far ahead of playback: bounds client memory and barge-in cleanup
FALLBACK_LINE = "Sorry, I had trouble with that. Could you say it again?"
# Whisper's classic outputs on noise-only audio; "thank you" alone is left out because users do say it
_STT_HALLUCINATIONS = {"you", "thanks for watching", "thank you for watching"}
FIRST_CHUNK_MIN_WORDS = 3  # the first TTS chunk may end at a comma once it has this many words
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


def _wall(monotonic: float) -> float:
    """A time.monotonic() instant as epoch seconds (never in the past: playback end may have passed)."""
    return time.time() + max(0.0, monotonic - time.monotonic())


def _discard_speculation(task: asyncio.Task) -> None:
    """Speech resumed: drop the speculative result. Retrieves any exception (no "never retrieved" log)
    and cancels a prefetched LLM request that already started."""
    if task.cancelled() or task.exception():
        return
    _, prefetch = task.result()
    if prefetch:
        prefetch.cancel()


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
        agent: AgentDef | None = None,
    ):
        self._stt = stt
        self._llm = llm
        self._tts = tts
        self._voice = voice
        self._agent = agent or AGENTS["assistant"]
        self._conversation = Conversation()
        self._vad = vad
        self._send_json = send_json
        self._send_bytes = send_bytes

        self.state = "idle"
        self._audio_buffer = bytearray()
        self._speech_started = False
        self._silence_frames = 0
        self._pending_frames: list[bytes] = []
        self._playing_until = 0.0  # monotonic time the client should finish playing everything sent so far
        self._preroll: deque[bytes] = deque(maxlen=PREROLL_FRAMES)
        self._interrupt = asyncio.Event()
        self._turn_task: asyncio.Task | None = None
        # speculative transcription (+ prefetched first LLM step) of the current utterance
        self._stt_task: asyncio.Task | None = None
        # (text, playback end time) per chunk spoken this turn: on barge-in, what the user actually heard
        self._spoken: list[tuple[str, float]] = []
        self._turn_open = False  # this turn's user message is in the conversation
        self._turn_start = 0.0  # end of utterance, the zero point for the turn's latency trace
        self._trace = TurnTrace()
        # timed transcript (epoch seconds), sent to the client as it happens and kept for scoring/replay
        self.turns: list[dict] = []
        self._utterance_start = 0.0
        self._reply_start: float | None = None  # first reply audio sent this turn

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
            # Synthesis runs far faster than real time, so state is "idle" while the client is still playing
            # seconds of queued audio: treat that as speaking too, or the client is never told to stop.
            if self.state in ("thinking", "speaking") or time.monotonic() < self._playing_until:
                await self._barge_in()
            else:
                self._speech_started = True
                await self._set_state("listening")
            self._utterance_start = time.time() - len(self._preroll) * FRAME_MS / 1000
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
                self._stt_task = asyncio.create_task(self._speculate(bytes(self._audio_buffer)))
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
        self._turn_start = time.monotonic()
        stt_task = self._stt_task or asyncio.create_task(self._speculate(audio, prefetch=False))
        self._stt_task = None
        await self._set_state("thinking")
        # end from the audio itself (PCM16 @ 16kHz, minus the trailing silence), not arrival time
        speech_s = len(audio) / 32000 - SILENCE_FRAMES_END_OF_TURN * FRAME_MS / 1000
        span = (self._utterance_start, self._utterance_start + max(0.0, speech_s))
        self._turn_task = asyncio.create_task(self._process_turn(stt_task, span))

    async def open(self, text: str) -> None:
        """Agent speaks first: run a turn on `text` as a hidden user message (an instruction, never shown
        or logged as something the user said)."""
        opening = asyncio.get_running_loop().create_future()
        opening.set_result((text, None))
        self._interrupt.clear()
        self._turn_start = time.monotonic()
        await self._set_state("thinking")
        self._turn_task = asyncio.create_task(self._process_turn(opening))

    async def drain(self) -> None:
        """Wait for the current turn to finish and its audio to finish playing on the client."""
        if self._turn_task:
            await asyncio.wait([self._turn_task])
        await asyncio.sleep(max(0.0, self._playing_until - time.monotonic()) + 0.5)

    async def _log_turn(self, role: str, text: str, start: float, end: float) -> None:
        turn = {"role": role, "text": text, "start": round(start, 3), "end": round(end, 3)}
        # a reply cut short after it was logged is the same reply (same start): replace, don't duplicate
        if self.turns and self.turns[-1]["role"] == role and self.turns[-1]["start"] == turn["start"]:
            self.turns[-1] = turn
        else:
            self.turns.append(turn)
        await self._send_json({"type": "turn", "data": turn})

    async def _transcribe(self, audio: bytes) -> str:
        transcript = ""
        async for event in self._stt.transcribe_stream(audio):
            if event.is_final:
                transcript = event.text
        return transcript

    async def _speculate(self, audio: bytes, prefetch: bool = True) -> tuple[str, Prefetch | None]:
        transcript = await self._transcribe(audio)
        if not prefetch or not _is_usable_transcript(transcript):
            return transcript, None
        messages = self._conversation.preview_messages(self._agent.system_prompt, transcript)
        return transcript, Prefetch(self._llm, self._agent, messages)

    def _cancel_speculative_stt(self) -> None:
        if self._stt_task:
            self._stt_task.add_done_callback(_discard_speculation)
            self._stt_task.cancel()
            self._stt_task = None

    def _elapsed_ms(self) -> float:
        return round((time.monotonic() - self._turn_start) * 1000)

    async def _process_turn(self, stt_task: Awaitable, span: tuple[float, float] | None = None) -> None:
        """`span` = when the user spoke (epoch seconds); None for a hidden opening turn."""
        speaker: asyncio.Task | None = None
        trace = self._trace = TurnTrace()
        self._spoken = []
        self._reply_start = None
        self._turn_open = False
        prefetch: Prefetch | None = None
        try:
            transcript, prefetch = await stt_task
            trace.stt_ms = self._elapsed_ms()
            logger.info("transcript: %r", transcript)
            if not _is_usable_transcript(transcript) or self._interrupt.is_set():
                await self._set_state("idle")
                return
            if span:
                await self._send_json({"type": "partial_transcript", "data": transcript})
                await self._log_turn("user", transcript, *span)
            # the conversation can change after the speculative request was built (a late tool note):
            # only reuse it if it's exactly the request this turn would send now
            if prefetch and prefetch.messages != self._conversation.preview_messages(self._agent.system_prompt, transcript):
                prefetch.cancel()
                prefetch = None
            self._conversation.add_user(transcript)
            self._turn_open = True

            await self._set_state("speaking")
            # agent and TTS run concurrently: generation keeps streaming into the queue while earlier
            # chunks are being synthesized, instead of stalling for each chunk's synthesis
            queue: asyncio.Queue[tuple[str, bool] | None] = asyncio.Queue()
            speaker = asyncio.create_task(self._speaker(queue))
            buf = ""
            reply = ""
            first = True
            async with aclosing(run_turn(self._conversation, self._agent, self._llm, trace, prefetch)) as events:
                async for event in events:
                    if self._interrupt.is_set():
                        break
                    if isinstance(event, Speak):
                        await self._send_json({"type": "token", "data": event.text})
                        buf += event.text
                        reply += event.text
                        while split := _split_speakable(buf, first):
                            chunk, buf = split
                            queue.put_nowait((chunk, True))
                            first = False
                    elif isinstance(event, Filler):
                        queue.put_nowait((event.text, False))  # not part of the reply: kept out of history
                    else:
                        # tool boundary: flush the preamble ("let me check") now; the answer after the
                        # tool gets the fast first-chunk split again
                        if buf.strip():
                            queue.put_nowait((buf, True))
                        buf = ""
                        first = True
                        status = "started" if isinstance(event, ToolStarted) else "finished"
                        data = {"name": event.name, "status": status}
                        if isinstance(event, ToolFinished):
                            data |= {"ms": round(event.ms), "ok": event.ok}
                        await self._send_json({"type": "tool", "data": data})
            if buf.strip() and not self._interrupt.is_set():
                queue.put_nowait((buf, True))
            queue.put_nowait(None)
            await speaker
            if self._spoken and self._reply_start is not None:
                heard = "".join(t for t, _ in self._spoken).strip()
                await self._log_turn("assistant", heard, self._reply_start, _wall(self._playing_until))
            logger.info("reply: %r", reply)
            trace.total_ms = self._elapsed_ms()
            logger.info("turn trace: %s", json.dumps(asdict(trace)))
            await self._send_json({"type": "trace", "data": asdict(trace)})

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
                await self._speak(FALLBACK_LINE, record=False)
            except Exception:
                logger.exception("fallback speech failed")
            await self._set_state("idle")
        finally:
            if speaker:
                speaker.cancel()
            if prefetch:
                prefetch.cancel()  # unused (unusable transcript, cancelled before the loop): abort it

    async def _speaker(self, queue: "asyncio.Queue[tuple[str, bool] | None]") -> None:
        while (item := await queue.get()) is not None:
            await self._speak(*item)

    async def _speak(self, text: str, record: bool = True) -> None:
        text = _strip_markdown(text)
        if not text.strip():
            return
        # aclosing: breaking out on interrupt must close the TTS stream now, not whenever GC gets to it
        async with aclosing(self._tts.synthesize_stream(text, voice=self._voice)) as stream:
            async for chunk in stream:
                lead = self._playing_until - time.monotonic()
                if lead > TTS_MAX_LEAD_S:
                    await asyncio.sleep(lead - TTS_MAX_LEAD_S)
                if self._interrupt.is_set():
                    return
                await self._send_bytes(chunk)
                if record and self._reply_start is None:
                    self._reply_start = time.time()
                if self._trace.first_audio_ms is None:
                    self._trace.first_audio_ms = self._elapsed_ms()
                self._playing_until = max(time.monotonic(), self._playing_until) + len(chunk) / TTS_BYTES_PER_SEC
        if record:
            self._spoken.append((text + " ", self._playing_until))

    async def _stop_turn(self) -> None:
        """Cancel whatever turn is in flight (LLM stream, tools, TTS, speculative STT), then rewrite the
        conversation to what the user actually heard. Cancelling the turn task closes the LLM stream,
        which aborts the HTTP request, so a self-hosted server frees the batch slot right away."""
        self._interrupt.set()
        now = time.monotonic()
        task = self._turn_task
        running = task is not None and not task.done()
        if running:
            task.cancel()
            await asyncio.wait([task])  # let the agent loop record tool results before history is rewritten
        self._cancel_speculative_stt()
        if (running and self._turn_open) or any(end > now for _, end in self._spoken):
            heard = "".join(t for t, end in self._spoken if end <= now)
            self._conversation.mark_interrupted(heard)
            if heard.strip() and self._reply_start is not None:
                await self._log_turn("assistant", heard.strip(), self._reply_start, time.time())
        self._spoken = []
        self._turn_open = False

    async def _barge_in(self) -> None:
        logger.info("barge-in detected")
        await self._stop_turn()
        self._playing_until = 0.0
        await self._send_json({"type": "interrupt"})
        self._audio_buffer.clear()
        self._speech_started = True
        self._silence_frames = 0
        await self._set_state("listening")

    async def interrupt(self) -> None:
        """Client-initiated stop (tap on the orb): drop the current reply and wait for new speech.
        No-op when nothing is in flight. The client already stopped its own playback."""
        self._playing_until = 0.0
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
