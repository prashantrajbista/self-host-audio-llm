"""Recording voice disguise: plumbing (decode, channel split, mix, encode) with a stand-in, then the real Praat
shift on synthetic voiced signals. No models, no network. Run: python -m tests.test_voice_anon
"""

import io

import av
import numpy as np
import parselmouth

from server.services.voice_anon import OUT_SR, SHIFT_DOWN, SHIFT_UP, anonymize_recording, decode, disguise, median_pitch

SECONDS = 3


def tone(hz: float, seconds: float = SECONDS) -> np.ndarray:
    return (0.3 * np.sin(2 * np.pi * hz * np.arange(int(OUT_SR * seconds)) / OUT_SR)).astype(np.float32)


def voice(f0: float, seconds: float = SECONDS) -> np.ndarray:
    """A crude voiced sound: harmonics of f0 with falling strength."""
    t = np.arange(int(OUT_SR * seconds)) / OUT_SR
    return (0.3 * sum(np.sin(2 * np.pi * f0 * k * t) / k for k in range(1, 15)) / 3).astype(np.float32)


def webm(channels: np.ndarray) -> bytes:
    layout = "stereo" if len(channels) == 2 else "mono"
    buf = io.BytesIO()
    with av.open(buf, "w", format="webm") as c:
        s = c.add_stream("libopus", rate=OUT_SR, layout=layout)
        frame = av.AudioFrame.from_ndarray(np.ascontiguousarray(channels), format="fltp", layout=layout)
        frame.sample_rate = OUT_SR
        for p in [*s.encode(frame), *s.encode(None)]:
            c.mux(p)
    return buf.getvalue()


def level(x: np.ndarray, hz: float) -> float:
    return float(np.abs(np.fft.rfft(x))[int(round(hz * len(x) / OUT_SR))])


def pitch_of(x: np.ndarray) -> float:
    return median_pitch(parselmouth.Sound(x.astype(np.float64), sampling_frequency=OUT_SR))


def main():
    # plumbing, with a stand-in for the disguise
    cand, ai = tone(220), tone(660)
    out = decode(anonymize_recording(webm(np.stack([cand, ai])), convert=np.zeros_like))
    assert out.shape[0] == 1, "stored mono"
    assert abs(out.shape[1] - len(cand)) < OUT_SR * 0.05, ("same length", out.shape[1], len(cand))
    assert level(out[0], 660) > 50 * level(out[0], 220), "interviewer kept, candidate replaced"
    out = decode(anonymize_recording(webm(np.stack([cand, ai])), convert=lambda x: x))
    assert level(out[0], 220) > 0.3 * level(out[0], 660), "candidate mixed back in"
    seen = []
    decode(anonymize_recording(webm(cand[None]), convert=lambda x: seen.append(len(x)) or x))
    assert abs(seen[0] - len(cand)) < OUT_SR * 0.05, "mono upload: the whole mix is disguised"

    # the real shift: lower voices go up, higher voices go down, length exact
    low, high = voice(120), voice(210)
    for x, f0, (factor, _) in ((low, 120, SHIFT_UP), (high, 210, SHIFT_DOWN)):
        y = disguise(x)
        assert len(y) == len(x), "exact length: replay seeking holds"
        got = pitch_of(y)
        assert abs(got - f0 * factor) < 0.08 * f0 * factor, (f0, got, f0 * factor)
    silence = np.zeros(OUT_SR, dtype=np.float32)
    assert disguise(silence) is silence, "nothing voiced: unchanged"
    print("voice disguise PASS")


if __name__ == "__main__":
    main()
