from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

from server.gateway.ws_handler import websocket_endpoint

app = FastAPI()


@app.websocket("/ws")
async def ws_route(websocket: WebSocket):
    await websocket_endpoint(websocket)


app.mount("/", StaticFiles(directory="client", html=True), name="client")
