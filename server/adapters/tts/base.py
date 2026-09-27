from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class TTSAdapter(ABC):
    @abstractmethod
    async def synthesize_stream(self, text_chunk: str) -> AsyncIterator[bytes]:
        """Yield raw PCM16 audio bytes for the given text chunk."""
        ...
