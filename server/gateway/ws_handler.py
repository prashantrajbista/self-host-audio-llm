import logging

from fastapi import WebSocket, WebSocketDisconnect

from server.config import get_settings
from server.gateway.factory import get_llm, get_stt, get_tts
from server.gateway.session import VoiceSession
from server.vad.vad import VAD

logger = logging.getLogger(__name__)

FRAME_BYTES = 640  # 20ms of mono PCM16 @ 16kHz


async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    client = f"{ws.client.host}:{ws.client.port}" if ws.client else "unknown"
    logger.info("client connected: %s", client)

    settings = get_settings()
    logger.debug(
        "session backends: stt=%s llm=%s tts=%s", settings.stt_backend, settings.llm_backend, settings.tts_backend
    )
    session = VoiceSession(
        stt=get_stt(settings),
        llm=get_llm(settings),
        tts=get_tts(settings),
        vad=VAD(threshold=settings.vad_threshold),
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
        logger.info("client disconnected: %s", client)
    except Exception:
        logger.exception("session crashed: %s", client)
