from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class Message:
    role: str
    content: str


class LLMAdapter(ABC):
    @abstractmethod
    async def generate_stream(self, messages: list[Message]) -> AsyncIterator[str]:
        """Yield response tokens/text chunks as they're generated."""
        ...

    @abstractmethod
    async def cancel(self) -> None:
        """Stop an in-flight generation (barge-in)."""
        ...
