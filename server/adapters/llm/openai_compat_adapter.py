import json
from collections.abc import AsyncIterator

from server.adapters.http_client import shared_client
from server.adapters.llm.base import Done, LLMAdapter, LLMEvent, Message, TextDelta, ToolCall


class OpenAICompatAdapter(LLMAdapter):
    """Any OpenAI-compatible /v1/chat/completions server with SSE streaming: OpenAI, vLLM, Ollama (/v1)."""

    def __init__(self, name: str, endpoint: str, model: str, api_key: str = ""):
        self.name = name
        self._url = f"{endpoint.rstrip('/')}/v1/chat/completions"
        self._model = model
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    async def generate_stream(
        self, messages: list[Message], tools: list[dict] | None = None, **params
    ) -> AsyncIterator[LLMEvent]:
        payload = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
            "stream_options": {"include_usage": True},
            **params,
        }
        if tools:
            payload["tools"] = tools
        calls: dict[int, dict] = {}  # tool-call fragments arrive spread over many chunks, keyed by index
        finish_reason = None
        usage = None
        async with shared_client().stream("POST", self._url, json=payload, headers=self._headers) as response:
            if response.status_code >= 400:
                # body carries the actual reason (bad model name, tool calling not enabled on vLLM, ...)
                body = (await response.aread()).decode(errors="replace")[:500]
                raise RuntimeError(f"{self.name} LLM HTTP {response.status_code}: {body}")
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                usage = chunk.get("usage") or usage
                for choice in chunk.get("choices") or []:  # usage-only chunk has no choices
                    delta = choice.get("delta") or {}
                    if delta.get("content"):
                        yield TextDelta(delta["content"])
                    for tc in delta.get("tool_calls") or []:
                        call = calls.setdefault(tc.get("index", 0), {"id": "", "name": "", "arguments": ""})
                        call["id"] = tc.get("id") or call["id"]
                        fn = tc.get("function") or {}
                        call["name"] = call["name"] or fn.get("name") or ""
                        args = fn.get("arguments")
                        if isinstance(args, dict):  # some servers send parsed JSON instead of a string
                            args = json.dumps(args)
                        call["arguments"] += args or ""
                    finish_reason = choice.get("finish_reason") or finish_reason
        for i in sorted(calls):
            c = calls[i]
            yield ToolCall(id=c["id"] or f"call_{i}", name=c["name"], arguments=c["arguments"] or "{}")
        yield Done(finish_reason=finish_reason, usage=usage, backend=self.name)
