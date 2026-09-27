"""Phase 2 check: real WS pipeline end-to-end (Ollama/faster-whisper/Kokoro), no browser needed.
Run: python -m tests.test_ws_integration
"""

import numpy as np
import soundfile as sf
from starlette.testclient import TestClient

from server.main import app

FRAME_BYTES = 640


def main():
    audio, sr = sf.read("/tmp/test_sample.wav", dtype="float32")
    assert sr == 16000, f"expected 16kHz sample, got {sr}"
    pcm16 = (audio * 32767).astype(np.int16).tobytes()
    pcm16 += b"\x00" * (2000 * 640)  # trailing silence to trigger end-of-utterance

    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        for i in range(0, len(pcm16), FRAME_BYTES):
            ws.send_bytes(pcm16[i : i + FRAME_BYTES])

        states = []
        got_transcript = False
        got_audio = False
        for _ in range(400):
            msg = ws.receive()
            if "text" in msg:
                import json

                data = json.loads(msg["text"])
                if data["type"] == "state":
                    states.append(data["data"])
                    if data["data"] == "idle" and "speaking" in states:
                        break
                if data["type"] == "partial_transcript":
                    got_transcript = True
                    print("transcript:", data["data"])
            elif "bytes" in msg:
                got_audio = True

    assert "listening" in states, states
    assert "thinking" in states, states
    assert "speaking" in states, states
    assert got_transcript
    assert got_audio
    print("states:", states)
    print("PASS")


if __name__ == "__main__":
    main()
