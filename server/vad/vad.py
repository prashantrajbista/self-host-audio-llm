import numpy as np
import torch
from silero_vad import load_silero_vad

CHUNK_SAMPLES = 512  # Silero's native inference window at 16kHz


class VAD:
    def __init__(self, sample_rate: int = 16000, threshold: float = 0.5, device: str = "cpu"):
        # fresh model per instance (one per WS connection): the jit module carries recurrent
        # state across calls, so sharing one instance across concurrent sessions would let
        # their audio cross-contaminate each other's speech/silence decisions. Loading is
        # local/cheap (~ms, no network), unlike the STT/TTS models factory.py caches.
        self._model = load_silero_vad().to(device)
        self._model.reset_states()
        self._sample_rate = sample_rate
        self._threshold = threshold
        self._device = device
        self._buffer = bytearray()
        self._last_is_speech = False

    def is_speech(self, frame: bytes) -> bool:
        """frame is mono PCM16 at the configured sample rate, any length; internally
        rebuffered to Silero's fixed 512-sample window, so the decision returned can lag
        by up to one window behind the frame just passed in."""
        self._buffer.extend(frame)
        chunk_bytes = CHUNK_SAMPLES * 2  # PCM16 = 2 bytes/sample
        while len(self._buffer) >= chunk_bytes:
            chunk = bytes(self._buffer[:chunk_bytes])
            del self._buffer[:chunk_bytes]
            samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
            with torch.no_grad():
                prob = self._model(torch.from_numpy(samples).to(self._device), self._sample_rate).item()
            self._last_is_speech = prob >= self._threshold
        return self._last_is_speech
