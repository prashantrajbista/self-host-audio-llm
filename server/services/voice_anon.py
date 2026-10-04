"""Stored-recording voice disguise: the candidate's side of the call is pitch- and formant-shifted (Praat's
"Change gender", PSOLA) so it sounds like a different person. Words, timing and intonation stay, at full
quality. Not irreversible: someone who knows the factors could shift it back. Runs on CPU, after the call.

The client records stereo: left = candidate mic, right = interviewer (already synthetic, kept as is). A mono
upload (older client) is disguised whole, interviewer included."""

import io
import math

import av
import numpy as np
import parselmouth
from parselmouth.praat import call

OUT_SR = 48000
PITCH_FLOOR, PITCH_CEILING = 75, 600
SPLIT_HZ = 165  # median pitch below this: shift up, otherwise down, so nobody ends up at an extreme
# the tuning knob: (pitch factor, formant factor) per direction. Pitch alone sounds like a chipmunk; moving the
# formants with it is what makes it sound like another person.
SHIFT_UP = (1.35, 1.12)
SHIFT_DOWN = (0.75, 0.90)


def decode(data: bytes) -> np.ndarray:
    """Any browser recording (webm/opus, mp4/aac) -> float32 (channels, samples) at OUT_SR."""
    with av.open(io.BytesIO(data)) as container:
        stream = container.streams.audio[0]
        layout = "stereo" if stream.channels >= 2 else "mono"
        resampler = av.AudioResampler(format="fltp", layout=layout, rate=OUT_SR)
        chunks = [f.to_ndarray() for frame in container.decode(stream) for f in resampler.resample(frame)]
        chunks += [f.to_ndarray() for f in resampler.resample(None)]
    return np.concatenate(chunks, axis=1).astype(np.float32)


def encode(mono: np.ndarray) -> bytes:
    buf = io.BytesIO()
    with av.open(buf, "w", format="webm") as container:
        stream = container.add_stream("libopus", rate=OUT_SR, layout="mono")
        frame = av.AudioFrame.from_ndarray(mono[None].astype(np.float32), format="flt", layout="mono")
        frame.sample_rate = OUT_SR
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    return buf.getvalue()


def median_pitch(sound: parselmouth.Sound) -> float:
    """Median pitch of the voiced parts in Hz; NaN if there's no voiced speech."""
    pitch = sound.to_pitch(pitch_floor=PITCH_FLOOR, pitch_ceiling=PITCH_CEILING)
    return call(pitch, "Get quantile", 0, 0, 0.5, "Hertz")


def disguise(x: np.ndarray) -> np.ndarray:
    """Candidate speech at OUT_SR -> same length, different-sounding voice. No voiced speech: returned as is."""
    sound = parselmouth.Sound(x.astype(np.float64), sampling_frequency=OUT_SR)
    median = median_pitch(sound)
    if math.isnan(median):
        return x
    pitch_factor, formant_factor = SHIFT_UP if median < SPLIT_HZ else SHIFT_DOWN
    shifted = call(sound, "Change gender", PITCH_FLOOR, PITCH_CEILING, formant_factor, median * pitch_factor, 1.0, 1.0)
    y = shifted.values[0].astype(np.float32)
    out = np.zeros_like(x)  # PSOLA can gain or lose a few samples: keep the exact length so replay seeking holds
    out[: min(len(x), len(y))] = y[: len(x)]
    return out


def anonymize_recording(data: bytes, convert=disguise) -> bytes:
    """Recording as uploaded -> mono webm with the candidate's voice disguised."""
    audio = decode(data)
    mix = convert(audio[0])
    if len(audio) > 1:
        mix = mix + audio[1]
    return encode(np.clip(mix, -1.0, 1.0))
