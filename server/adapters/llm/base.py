from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON, as the model produced it


@dataclass
class Message:
    role: str
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None

    def to_dict(self) -> dict:
        d: dict = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = [
                {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
                for c in self.tool_calls
            ]
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class TextDelta:
    text: str


@dataclass
class Done:
    finish_reason: str | None
    usage: dict | None
    backend: str


LLMEvent = TextDelta | ToolCall | Done


class LLMAdapter(ABC):
    """Stateless: cancelling a generation = closing the generator (aborts the HTTP request),
    so one instance is shared by every session in the process."""

    @abstractmethod
    def generate_stream(
        self, messages: list[Message], tools: list[dict] | None = None, **params
    ) -> AsyncIterator[LLMEvent]:
        """Yield TextDelta as text streams, then any ToolCall (arguments complete), then Done."""
        ...
