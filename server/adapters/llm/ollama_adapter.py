import asyncio
import json
from collections.abc import AsyncIterator

from server.adapters.http_client import shared_client
from server.adapters.llm.base import LLMAdapter, Message


class OllamaAdapter(LLMAdapter):
    def __init__(self, endpoint: str = "http://localhost:11434", model: str = "llama3.2"):
        self._endpoint = endpoint
        self._model = model
        self._cancelled = asyncio.Event()

    async def generate_stream(self, messages: list[Message]) -> AsyncIterator[str]:
        self._cancelled.clear()
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }
        client = shared_client()
        async with client.stream("POST", f"{self._endpoint}/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if self._cancelled.is_set():
                    break
                if not line:
                    continue
                data = json.loads(line)
                content = data.get("message", {}).get("content", "")
                if content:
                    yield content
                if data.get("done"):
                    break

    async def cancel(self) -> None:
        self._cancelled.set()
