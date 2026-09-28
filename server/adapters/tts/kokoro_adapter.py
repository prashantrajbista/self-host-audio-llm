import asyncio
from collections.abc import AsyncIterator

import numpy as np
from kokoro import KPipeline

from server.adapters.tts.base import TTSAdapter


class KokoroAdapter(TTSAdapter):
    def __init__(self, voice: str = "af_heart", lang_code: str = "a", device: str = "cpu"):
        self._pipeline = KPipeline(lang_code=lang_code, device=device)
        self._voice = voice
        # one shared model across sessions: serialize inference steps rather than trusting the
        # pipeline to be thread-safe under concurrent calls
        self._lock = asyncio.Lock()
        # warm-up: first synthesis pays voice load + lazy init; take it at load, not on the first reply
        for _ in self._pipeline("Hello.", voice=voice):
            pass

    async def synthesize_stream(self, text_chunk: str) -> AsyncIterator[bytes]:
        results = self._pipeline(text_chunk, voice=self._voice)
        while True:
            # each generator step runs inference; step it in a worker thread so the event loop
            # keeps receiving mic frames (barge-in) while audio is being synthesized
            async with self._lock:
                result = await asyncio.to_thread(next, results, None)
            if result is None:
                return
            _, _, audio = result
            pcm16 = (np.asarray(audio) * 32767).astype(np.int16)
            yield pcm16.tobytes()
