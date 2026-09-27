from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

from server.config import get_settings
from server.gateway.ws_handler import websocket_endpoint
from server.logging_config import setup_logging

setup_logging(get_settings().log_level)

app = FastAPI()


@app.websocket("/ws")
async def ws_route(websocket: WebSocket):
    await websocket_endpoint(websocket)


app.mount("/", StaticFiles(directory="client", html=True), name="client")
