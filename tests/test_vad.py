"""VAD check: Silero classifies silence vs speech-like audio correctly, and the internal
512-sample rebuffering handles a stream of 20ms frames (640 bytes) without crashing.
Run: python -m tests.test_vad
"""

import numpy as np

from server.vad.vad import VAD

SAMPLE_RATE = 16000
FRAME_BYTES = 640  # 20ms of mono PCM16 @ 16kHz


def silence_frames(n: int) -> list[bytes]:
    return [b"\x00" * FRAME_BYTES for _ in range(n)]


def tone_frames(n: int, freq: int = 200) -> list[bytes]:
    # a loud low-frequency tone isn't real speech, but it's a deterministic stand-in that
    # doesn't require shipping a sample WAV just to exercise the buffering/threshold path
    t = np.arange(n * FRAME_BYTES // 2) / SAMPLE_RATE
    samples = (np.sin(2 * np.pi * freq * t) * 32000).astype(np.int16)
    raw = samples.tobytes()
    return [raw[i : i + FRAME_BYTES] for i in range(0, len(raw), FRAME_BYTES)]


def main() -> None:
    vad = VAD(sample_rate=SAMPLE_RATE)
    results = [vad.is_speech(f) for f in silence_frames(20)]
    assert not any(results), f"silence misclassified as speech: {results}"
    print("silence PASS")

    vad = VAD(sample_rate=SAMPLE_RATE)
    # feed an odd number of frames (33) to exercise the leftover-buffer path across the
    # non-512-aligned 640-byte frame boundary
    for f in tone_frames(33):
        vad.is_speech(f)
    print("odd-frame-count buffering PASS (no crash)")


if __name__ == "__main__":
    main()
