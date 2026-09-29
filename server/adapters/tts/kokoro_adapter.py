import asyncio
from collections.abc import AsyncIterator

import numpy as np
from kokoro import KPipeline

from server.adapters.tts.base import TTSAdapter


FADE_SAMPLES = 72  # 3ms @ 24kHz: de-clicks the seam between synthesized segments


def _fade_edges(audio: np.ndarray) -> np.ndarray:
    n = min(FADE_SAMPLES, len(audio) // 2)
    if n:
        ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
        audio = audio.astype(np.float32, copy=True)
        audio[:n] *= ramp
        audio[-n:] *= ramp[::-1]
    return audio


class KokoroAdapter(TTSAdapter):
    def __init__(
        self, voice: str = "af_heart", lang_code: str = "a", device: str = "cpu", voices: tuple[str, ...] = (),
        speed: float = 1.0,
    ):
        self._pipeline = KPipeline(lang_code=lang_code, device=device)
        self._voice = voice
        self._speed = speed
        # one shared model across sessions: serialize inference steps rather than trusting the
        # pipeline to be thread-safe under concurrent calls
        self._lock = asyncio.Lock()
        # warm-up: first synthesis pays voice load + lazy init; take it at load, not on the first reply.
        # Preload every selectable voice too, so picking one never waits on a download.
        for v in voices:
            self._pipeline.load_voice(v)
        for _ in self._pipeline("Hello.", voice=voice):
            pass

    async def synthesize_stream(self, text_chunk: str, voice: str | None = None) -> AsyncIterator[bytes]:
        results = self._pipeline(text_chunk, voice=voice or self._voice, speed=self._speed)
        try:
            while True:
                # each generator step runs inference; step it in a worker thread so the event loop
                # keeps receiving mic frames (barge-in) while audio is being synthesized
                async with self._lock:
                    result = await self._step(results)
                if result is None:
                    return
                _, _, audio = result
                pcm16 = (_fade_edges(np.asarray(audio)) * 32767).astype(np.int16)
                yield pcm16.tobytes()
        finally:
            results.close()  # barge-in abandons the stream: don't leave the pipeline generator half-run

    @staticmethod
    async def _step(results):
        """One generator step in a worker thread. A cancel can't stop the thread, so wait it out before
        propagating: otherwise the lock is released while inference still runs and the next caller
        would use the pipeline concurrently."""
        task = asyncio.ensure_future(asyncio.to_thread(next, results, None))
        task.add_done_callback(lambda t: t.cancelled() or t.exception())  # mark retrieved
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            await asyncio.wait({task})
            raise
