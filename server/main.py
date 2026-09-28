from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket

from server.config import get_settings
from server.gateway.factory import get_stt, get_tts
from server.gateway.ws_handler import websocket_endpoint
from server.logging_config import setup_logging

setup_logging(get_settings().log_level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # load + warm the cached STT/TTS models at boot, not on the first WS connection
    settings = get_settings()
    get_stt(settings)
    get_tts(settings)
    yield


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def ws_route(websocket: WebSocket):
    await websocket_endpoint(websocket)
