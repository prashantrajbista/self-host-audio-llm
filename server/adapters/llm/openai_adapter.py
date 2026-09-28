import asyncio
import json
from collections.abc import AsyncIterator

import httpx

from server.adapters.llm.base import LLMAdapter, Message


class OpenAIAdapter(LLMAdapter):
    """Talks to OpenAI's chat completions API (/v1/chat/completions, SSE streaming)."""

    def __init__(
        self,
        endpoint: str = "https://api.openai.com",
        model: str = "gpt-4o-mini",
        api_key: str = "",
    ):
        self._endpoint = endpoint
        self._model = model
        self._api_key = api_key
        self._cancelled = asyncio.Event()

    async def generate_stream(self, messages: list[Message]) -> AsyncIterator[str]:
        self._cancelled.clear()
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", f"{self._endpoint}/v1/chat/completions", json=payload, headers=headers
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if self._cancelled.is_set():
                        break
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[len("data:") :].strip()
                    if data_str == "[DONE]":
                        break
                    data = json.loads(data_str)
                    delta = data["choices"][0]["delta"].get("content")
                    if delta:
                        yield delta

    async def cancel(self) -> None:
        self._cancelled.set()
