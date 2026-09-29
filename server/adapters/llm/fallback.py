import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import aclosing

from server.adapters.llm.base import LLMAdapter, LLMEvent, Message

logger = logging.getLogger(__name__)

FAILURE_THRESHOLD = 3  # consecutive failures before a backend's circuit opens
COOLDOWN_S = 30.0  # how long an open circuit skips the backend


class FallbackLLM(LLMAdapter):
    """Tries backends in order until one produces a first event within `first_event_timeout`.
    Failover only happens before anything was yielded, so a reply is never repeated. With a single
    backend it retries that backend once. Circuit state is process-wide (shared by all sessions),
    so a dead backend costs one timeout per cooldown window, not one per call."""

    def __init__(self, backends: list[LLMAdapter], first_event_timeout: float):
        self._backends = backends if len(backends) > 1 else backends * 2
        self._timeout = first_event_timeout
        self._failures: dict[int, int] = {}
        self._open_until: dict[int, float] = {}

    def _is_open(self, backend: LLMAdapter) -> bool:
        return self._open_until.get(id(backend), 0.0) > time.monotonic()

    def _record(self, backend: LLMAdapter, ok: bool) -> None:
        key = id(backend)
        if ok:
            self._failures[key] = 0
            return
        self._failures[key] = self._failures.get(key, 0) + 1
        if self._failures[key] >= FAILURE_THRESHOLD:
            self._open_until[key] = time.monotonic() + COOLDOWN_S
            logger.warning("llm circuit open for %s (%.0fs)", getattr(backend, "name", backend), COOLDOWN_S)

    async def generate_stream(
        self, messages: list[Message], tools: list[dict] | None = None, **params
    ) -> AsyncIterator[LLMEvent]:
        # all circuits open: try them anyway rather than fail the call outright
        candidates = [b for b in self._backends if not self._is_open(b)] or self._backends
        for i, backend in enumerate(candidates):
            got_event = False
            try:
                async with aclosing(backend.generate_stream(messages, tools, **params)) as stream:
                    while True:
                        try:
                            if got_event:
                                event = await anext(stream)
                            else:
                                async with asyncio.timeout(self._timeout):
                                    event = await anext(stream)
                                got_event = True
                                self._record(backend, ok=True)
                        except StopAsyncIteration:
                            return
                        yield event
            except Exception:
                self._record(backend, ok=False)
                if got_event or i == len(candidates) - 1:
                    raise
                logger.warning("llm %s failed before first event, trying next", getattr(backend, "name", backend), exc_info=True)
