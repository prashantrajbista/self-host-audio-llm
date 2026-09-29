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
        speed: float = 1.0, workers: int = 1,
    ):
        self._voice = voice
        self._speed = speed
        # pool of independent pipelines: each sentence borrows one, so concurrent calls synthesize in
        # parallel instead of queueing on a single lock. Pipelines aren't shared between threads, so no
        # reliance on KPipeline being thread-safe.
        self._pool: asyncio.Queue[KPipeline] = asyncio.Queue()
        for _ in range(max(1, workers)):
            pipeline = KPipeline(lang_code=lang_code, device=device)
            # warm-up: first synthesis pays voice load + lazy init; take it at load, not on the first reply.
            # Preload every selectable voice too, so picking one never waits on a download.
            for v in voices:
                pipeline.load_voice(v)
            for _ in pipeline("Hello.", voice=voice):
                pass
            self._pool.put_nowait(pipeline)

    async def synthesize_stream(self, text_chunk: str, voice: str | None = None) -> AsyncIterator[bytes]:
        # held for the whole sentence: a pipeline's generator can only be stepped on the pipeline that made it
        pipeline = await self._pool.get()
        try:
            results = pipeline(text_chunk, voice=voice or self._voice, speed=self._speed)
            try:
                while True:
                    # each generator step runs inference; step it in a worker thread so the event loop
                    # keeps receiving mic frames (barge-in) while audio is being synthesized
                    result = await self._step(results)
                    if result is None:
                        return
                    _, _, audio = result
                    pcm16 = (_fade_edges(np.asarray(audio)) * 32767).astype(np.int16)
                    yield pcm16.tobytes()
            finally:
                results.close()  # barge-in abandons the stream: don't leave the pipeline generator half-run
        finally:
            self._pool.put_nowait(pipeline)

    @staticmethod
    async def _step(results):
        """One generator step in a worker thread. A cancel can't stop the thread, so wait it out before
        propagating: otherwise the pipeline goes back to the pool while inference still runs on it and
        the next caller would use it concurrently."""
        task = asyncio.ensure_future(asyncio.to_thread(next, results, None))
        task.add_done_callback(lambda t: t.cancelled() or t.exception())  # mark retrieved
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            await asyncio.wait({task})
            raise
