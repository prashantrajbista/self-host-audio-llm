"""Who and what the current work is for. Set once (call start, authenticated request); asyncio tasks created
afterwards inherit it, so logs, traces, error reports and LLM spans all carry it without passing it around."""

from contextvars import ContextVar

session_id: ContextVar[str | None] = ContextVar("session_id", default=None)  # the interview id
user_id: ContextVar[str | None] = ContextVar("user_id", default=None)
llm_call: ContextVar[str] = ContextVar("llm_call", default="llm")  # what an LLM request is for, e.g. "interviewer"
