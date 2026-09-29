import asyncio
import io
from collections.abc import AsyncIterator

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

from server.adapters.stt.base import STTAdapter, TranscriptEvent


class FasterWhisperAdapter(STTAdapter):
    def __init__(self, model_size: str = "base.en", device: str = "cpu"):
        compute_type = "int8" if device == "cpu" else "float16"
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
        # warm-up: the first transcribe pays one-time init cost; take it at load, not on the first user turn
        self._transcribe_sync(np.zeros(16000, dtype=np.int16).tobytes())

    def _transcribe_sync(self, audio_chunk: bytes) -> str:
        if audio_chunk[:4] == b"RIFF":
            audio, _ = sf.read(io.BytesIO(audio_chunk), dtype="float32")
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)
        else:
            # raw PCM16 mono 16kHz, as sent over the WS mic stream
            audio = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        # quiet speech reaches Whisper at low level and gets misheard: boost to ~-3dBFS (never attenuate;
        # gain capped and near-silence skipped so noise-only audio isn't blown up)
        peak = float(np.abs(audio).max()) if audio.size else 0.0
        if peak > 0.005:
            audio = audio * min(10.0, max(1.0, 0.7 / peak))
        # greedy decode, no timestamps, no cross-window conditioning: ~2x faster than defaults,
        # negligible accuracy loss on short voice-turn utterances
        segments, _ = self._model.transcribe(
            audio, language="en", beam_size=1, without_timestamps=True, condition_on_previous_text=False
        )
        # segments is lazy — the actual decode runs during this join, so it must stay in the thread
        # Whisper's own "this was silence" rule: high no-speech probability with a low-confidence decode is a
        # hallucination on noise ("Thank you.", "you"), not something the user said
        return " ".join(s.text.strip() for s in segments if not (s.no_speech_prob > 0.6 and s.avg_logprob < -1.0))

    async def transcribe_stream(self, audio_chunk: bytes) -> AsyncIterator[TranscriptEvent]:
        # off the event loop: inference here blocked WS receive (and barge-in detection) for its full duration
        text = await asyncio.to_thread(self._transcribe_sync, audio_chunk)
        yield TranscriptEvent(text=text, is_final=True)
