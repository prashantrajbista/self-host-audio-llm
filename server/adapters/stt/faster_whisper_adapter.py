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

    async def transcribe_stream(self, audio_chunk: bytes) -> AsyncIterator[TranscriptEvent]:
        if audio_chunk[:4] == b"RIFF":
            audio, _ = sf.read(io.BytesIO(audio_chunk), dtype="float32")
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)
        else:
            # raw PCM16 mono 16kHz, as sent over the WS mic stream
            audio = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = self._model.transcribe(audio, language="en")
        text = " ".join(segment.text.strip() for segment in segments)
        yield TranscriptEvent(text=text, is_final=True)
