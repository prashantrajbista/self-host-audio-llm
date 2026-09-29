import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from server.agent.agents import get_agent
from server.config import get_settings, resolve_voice
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
    agent = get_agent(ws.query_params.get("agent"), settings.agent)
    # client's pick wins, then the agent's own voice, then the configured default
    voice = resolve_voice(settings, ws.query_params.get("voice") or agent.voice)
    logger.debug(
        "session backends: stt=%s llm=%s tts=%s voice=%s agent=%s",
        settings.stt_backend,
        settings.llm_backend,
        settings.tts_backend,
        voice,
        agent.name,
    )
    session = VoiceSession(
        stt=get_stt(settings),
        llm=get_llm(settings),
        tts=get_tts(settings),
        vad=VAD(threshold=settings.vad_threshold),
        send_json=ws.send_json,
        send_bytes=ws.send_bytes,
        voice=voice,
        agent=agent,
    )

    buffer = bytearray()
    try:
        while True:
            # binary frames = mic audio; text frames = JSON control messages from the client
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(message.get("code", 1000))
            if message.get("bytes") is not None:
                buffer.extend(message["bytes"])
                while len(buffer) >= FRAME_BYTES:
                    frame = bytes(buffer[:FRAME_BYTES])
                    del buffer[:FRAME_BYTES]
                    await session.handle_audio_frame(frame)
            elif message.get("text") is not None:
                control = json.loads(message["text"])
                if control.get("type") == "interrupt":
                    await session.interrupt()
    except WebSocketDisconnect:
        logger.info("client disconnected: %s", client)
    except Exception:
        logger.exception("session crashed: %s", client)
    finally:
        session.close()
