from abc import ABC, abstractmethod


class CodecAdapter(ABC):
    @abstractmethod
    def encode(self, audio: bytes) -> bytes:
        """Compress raw PCM16 audio into codec tokens."""
        ...

    @abstractmethod
    def decode(self, tokens: bytes) -> bytes:
        """Decompress codec tokens back into raw PCM16 audio."""
        ...
