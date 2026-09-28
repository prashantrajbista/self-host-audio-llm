from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class TTSAdapter(ABC):
    @abstractmethod
    async def synthesize_stream(self, text_chunk: str, voice: str | None = None) -> AsyncIterator[bytes]:
        """Yield raw PCM16 audio bytes for the given text chunk, in `voice` (adapter default if None)."""
        ...
