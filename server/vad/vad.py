import copy

import numpy as np
import torch
from silero_vad import load_silero_vad

CHUNK_SAMPLES = 512  # Silero's native inference window at 16kHz

_shared = None


def _shared_model():
    """Load the ONNX model once per process. ONNX over the torch.jit build: Silero's ONNX wrapper pins
    inference to one thread, where torch would fan every 32ms window out to all cores and have the
    sessions' threads fight each other. Always CPU: the model is tiny and runs every 32ms, so a GPU
    transfer per window costs more than the inference it would save."""
    global _shared
    if _shared is None:
        _shared = load_silero_vad(onnx=True)
    return _shared


def preload() -> None:
    _shared_model()


class VAD:
    def __init__(self, sample_rate: int = 16000, threshold: float = 0.5):
        # per-session copy: shares the (thread-safe) ONNX session, but the recurrent state and context
        # are this session's own, so concurrent sessions' audio can't cross-contaminate each other's
        # speech/silence decisions. reset_states() rebinds them to fresh tensors on the copy.
        # ponytail: inference still runs inline on the event loop (~0.1ms/window); batch windows across
        # sessions in one ONNX call if profiling shows loop lag at high session counts
        self._model = copy.copy(_shared_model())
        self._model.reset_states()
        self._sample_rate = sample_rate
        self._threshold = threshold
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
                prob = self._model(torch.from_numpy(samples), self._sample_rate).item()
            self._last_is_speech = prob >= self._threshold
        return self._last_is_speech
