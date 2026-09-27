"""Phase 5/7: end-to-end turn latency against a running gateway (real network WS, not in-process).

Measures, per turn: time to partial_transcript, time to first token, time to first audio_out,
total turn time (until state=idle). Prints p50/p95 across N turns.

Run: python -m eval.latency_bench --host localhost --port 8000 --wav /tmp/test_sample.wav --turns 5
"""

import argparse
import asyncio
import json
import statistics
import time

import websockets

FRAME_BYTES = 640


def load_pcm16_frames(wav_path: str) -> list[bytes]:
    import numpy as np
    import soundfile as sf

    audio, sr = sf.read(wav_path, dtype="float32")
    assert sr == 16000, f"expected 16kHz wav, got {sr}"
    pcm16 = (audio * 32767).astype(np.int16).tobytes()
    pcm16 += b"\x00" * (2000 * FRAME_BYTES)  # trailing silence to trigger end-of-utterance
    return [pcm16[i : i + FRAME_BYTES] for i in range(0, len(pcm16), FRAME_BYTES)]


async def run_turn(uri: str, frames: list[bytes]) -> dict:
    timings = {}
    t0 = time.monotonic()
    async with websockets.connect(uri) as ws:
        for frame in frames:
            await ws.send(frame)

        while True:
            msg = await ws.recv()
            now = time.monotonic() - t0
            if isinstance(msg, bytes):
                timings.setdefault("first_audio_out", now)
                continue
            data = json.loads(msg)
            if data["type"] == "partial_transcript":
                timings.setdefault("partial_transcript", now)
            elif data["type"] == "token":
                timings.setdefault("first_token", now)
            elif data["type"] == "state" and data["data"] == "idle" and "partial_transcript" in timings:
                timings["total"] = now
                break
    return timings


def percentile(values: list[float], p: float) -> float:
    return statistics.quantiles(values, n=100, method="inclusive")[int(p) - 1] if len(values) > 1 else values[0]


async def main(host: str, port: int, wav: str, turns: int):
    uri = f"ws://{host}:{port}/ws"
    frames = load_pcm16_frames(wav)
    results = []
    for i in range(turns):
        print(f"turn {i + 1}/{turns}...")
        results.append(await run_turn(uri, frames))

    for stage in ("partial_transcript", "first_token", "first_audio_out", "total"):
        values = [r[stage] for r in results if stage in r]
        if not values:
            continue
        p50 = percentile(values, 50)
        p95 = percentile(values, 95)
        print(f"{stage:20s} p50={p50 * 1000:.0f}ms  p95={p95 * 1000:.0f}ms  n={len(values)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--wav", default="/tmp/test_sample.wav")
    parser.add_argument("--turns", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(main(args.host, args.port, args.wav, args.turns))
