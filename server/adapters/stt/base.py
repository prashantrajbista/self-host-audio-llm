from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class TranscriptEvent:
    text: str
    is_final: bool


class STTAdapter(ABC):
    @abstractmethod
    async def transcribe_stream(self, audio_chunk: bytes) -> AsyncIterator[TranscriptEvent]:
        """Feed one chunk of PCM16 audio, yield partial/final transcript events."""
        ...
