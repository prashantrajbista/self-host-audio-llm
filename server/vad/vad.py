import webrtcvad

# ponytail: webrtcvad instead of Silero — no model download, deterministic, good enough
# for barge-in detection. Swap for Silero if speech/noise discrimination needs improve.


class VAD:
    def __init__(self, sample_rate: int = 16000, aggressiveness: int = 2):
        self._vad = webrtcvad.Vad(aggressiveness)
        self._sample_rate = sample_rate

    def is_speech(self, frame: bytes) -> bool:
        """frame must be 10/20/30ms of mono PCM16 at the configured sample rate."""
        return self._vad.is_speech(frame, self._sample_rate)
