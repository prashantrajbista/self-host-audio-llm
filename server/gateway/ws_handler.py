from fastapi import WebSocket, WebSocketDisconnect

from server.config import get_settings
from server.gateway.factory import get_llm, get_stt, get_tts
from server.gateway.session import VoiceSession
from server.vad.vad import VAD

FRAME_BYTES = 640  # 20ms of mono PCM16 @ 16kHz


async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    settings = get_settings()
    session = VoiceSession(
        stt=get_stt(settings),
        llm=get_llm(settings),
        tts=get_tts(settings),
        vad=VAD(),
        send_json=ws.send_json,
        send_bytes=ws.send_bytes,
    )

    buffer = bytearray()
    try:
        while True:
            chunk = await ws.receive_bytes()
            buffer.extend(chunk)
            while len(buffer) >= FRAME_BYTES:
                frame = bytes(buffer[:FRAME_BYTES])
                del buffer[:FRAME_BYTES]
                await session.handle_audio_frame(frame)
    except WebSocketDisconnect:
        pass
