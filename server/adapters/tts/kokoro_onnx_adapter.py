import asyncio
from collections.abc import AsyncIterator

import numpy as np
import onnxruntime as ort
from kokoro_onnx import Kokoro

from server.adapters.tts.base import TTSAdapter
from server.adapters.tts.kokoro_adapter import _fade_edges


class KokoroOnnxAdapter(TTSAdapter):
    """Kokoro through ONNX Runtime (int8 export): several times faster than the PyTorch pipeline on CPU.
    Phonemes come from espeak-ng rather than misaki, so a few words may be pronounced differently."""

    def __init__(
        self, model_path: str, voices_path: str, voice: str = "af_heart", speed: float = 1.0, workers: int = 1,
        threads: int = 0,
    ):
        self._voice = voice
        self._speed = speed
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads  # 0 = ONNX Runtime default (all cores)
        opts.inter_op_num_threads = 1
        session = ort.InferenceSession(model_path, opts, providers=["CPUExecutionProvider"])
        self._kokoro = Kokoro.from_session(session, voices_path)
        # one session is thread-safe; the semaphore caps sentences synthesized at once so they don't
        # oversubscribe the cores between them
        self._slots = asyncio.Semaphore(max(1, workers))
        self._kokoro.create("Hello.", voice=voice, speed=speed)  # warm-up: first run pays lazy init

    async def synthesize_stream(self, text_chunk: str, voice: str | None = None) -> AsyncIterator[bytes]:
        # the gateway already sends one sentence/clause per request, so synthesize it whole
        async with self._slots:
            task = asyncio.ensure_future(
                asyncio.to_thread(self._kokoro.create, text_chunk, voice=voice or self._voice, speed=self._speed)
            )
            task.add_done_callback(lambda t: t.cancelled() or t.exception())  # mark retrieved
            try:
                audio, _ = await asyncio.shield(task)
            except asyncio.CancelledError:
                # a cancel can't stop the thread: hold the slot until it finishes so the cap stays true
                await asyncio.wait({task})
                raise
        if len(audio):
            yield (_fade_edges(np.asarray(audio)) * 32767).astype(np.int16).tobytes()
