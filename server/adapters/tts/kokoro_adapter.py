from collections.abc import AsyncIterator

import numpy as np
from kokoro import KPipeline

from server.adapters.tts.base import TTSAdapter


class KokoroAdapter(TTSAdapter):
    def __init__(self, voice: str = "af_heart", lang_code: str = "a", device: str = "cpu"):
        self._pipeline = KPipeline(lang_code=lang_code, device=device)
        self._voice = voice

    async def synthesize_stream(self, text_chunk: str) -> AsyncIterator[bytes]:
        for _, _, audio in self._pipeline(text_chunk, voice=self._voice):
            pcm16 = (np.asarray(audio) * 32767).astype(np.int16)
            yield pcm16.tobytes()
