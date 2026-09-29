import asyncio
import json
import time
from collections.abc import AsyncIterator
from contextlib import aclosing
from dataclasses import dataclass, field

from server.adapters.llm.base import Done, LLMAdapter, Message, TextDelta, ToolCall
from server.agent.agents import AgentDef
from server.agent.conversation import Conversation
from server.agent.tools import Tool, execute

FILLER_DELAY_S = 0.4  # tools faster than this add no audio; slower ones get a filler line
DEFAULT_FILLER = "One moment."
CONFIRM_REQUIRED = (
    "NOT EXECUTED: this action needs the user's explicit confirmation. Read the details back to the user "
    "and ask them to confirm. Only if they agree in their next message, call it again with the same arguments."
)


@dataclass
class Speak:
    text: str


@dataclass
class Filler:
    text: str


@dataclass
class ToolStarted:
    name: str


@dataclass
class ToolFinished:
    name: str
    ms: float
    ok: bool


AgentEvent = Speak | Filler | ToolStarted | ToolFinished


@dataclass
class TurnTrace:
    stt_ms: float | None = None
    llm_ttft_ms: list[float] = field(default_factory=list)  # one per LLM step
    tools: list[dict] = field(default_factory=list)
    first_audio_ms: float | None = None
    total_ms: float | None = None
    backend: str | None = None
    usage: list[dict] = field(default_factory=list)


def _canonical(arguments: str) -> str:
    try:
        return json.dumps(json.loads(arguments or "{}"), sort_keys=True)
    except ValueError:
        return arguments


async def _call(conv: Conversation, t: Tool | None, call: ToolCall) -> tuple[str, float]:
    start = time.monotonic()
    if t is None:
        result = f"Error: unknown tool {call.name}."
    elif t.side_effect and conv.pending_confirmations.pop(key := (t.name, _canonical(call.arguments)), None) != conv.user_turns - 1:
        # enforced in code, not left to the prompt: execute only when the same call was proposed on the
        # previous turn (the user has spoken since). Confirmations are consumed, so no double execution.
        conv.pending_confirmations[key] = conv.user_turns
        result = CONFIRM_REQUIRED
    else:
        result = await execute(t, call.arguments)
    return result, (time.monotonic() - start) * 1000


def _abandon(conv: Conversation, tools: dict[str, Tool], calls: list[ToolCall], tasks: dict[str, asyncio.Task]) -> None:
    """Turn interrupted mid-tools: every tool call still gets a result message (the API requires it).
    Read-only tools are cancelled; side-effecting ones finish and report back as a note."""
    for c in calls:
        task, t = tasks[c.id], tools.get(c.name)
        if task.done() and not task.cancelled():
            result = task.result()[0]
        elif t and t.side_effect:
            result = "Still running when the user interrupted; its outcome will be shared in a note."
            task.add_done_callback(
                lambda tk, name=c.name: tk.cancelled() or conv.add_note(f"{name} finished: {tk.result()[0]}")
            )
        else:
            task.cancel()
            result = "Cancelled: the user interrupted before it finished."
        conv.add(Message(role="tool", content=result, tool_call_id=c.id))


async def _run_tools(
    conv: Conversation, tools: dict[str, Tool], calls: list[ToolCall], trace: TurnTrace
) -> AsyncIterator[AgentEvent]:
    tasks = {c.id: asyncio.create_task(_call(conv, tools.get(c.name), c)) for c in calls}
    try:
        for c in calls:
            yield ToolStarted(c.name)
        _, pending = await asyncio.wait(tasks.values(), timeout=FILLER_DELAY_S)
        if pending:
            slow = [tools[c.name].filler for c in calls if tasks[c.id] in pending and c.name in tools]
            yield Filler(next((f for f in slow if f), DEFAULT_FILLER))
            await asyncio.wait(pending)
    except BaseException:  # cancelled (barge-in) or generator closed
        _abandon(conv, tools, calls, tasks)
        raise
    # all results go into history before anything else is yielded, so a close here can't orphan a call
    results = [tasks[c.id].result() for c in calls]
    for c, (result, _) in zip(calls, results):
        conv.add(Message(role="tool", content=result, tool_call_id=c.id))
    for c, (result, ms) in zip(calls, results):
        ok = not result.startswith(("Error:", "NOT EXECUTED"))
        trace.tools.append({"name": c.name, "ms": round(ms), "ok": ok})
        yield ToolFinished(c.name, ms, ok)


async def run_turn(conv: Conversation, agent: AgentDef, llm: LLMAdapter, trace: TurnTrace) -> AsyncIterator[AgentEvent]:
    """LLM -> tools -> LLM ... until a reply without tool calls. The user message is already in `conv`.
    Text is yielded as it streams so TTS starts on the first clause, including a preamble before tools."""
    tools = {t.name: t for t in agent.tools}
    for step in range(agent.max_steps):
        # last step goes without tools, so the model has to answer from the results it already has
        schemas = agent.tool_schemas if step < agent.max_steps - 1 else None
        text, calls = "", []
        start = time.monotonic()
        stream = llm.generate_stream(conv.request_messages(agent.system_prompt), schemas, **agent.llm_params)
        async with aclosing(stream):
            async for event in stream:
                if isinstance(event, Done):
                    trace.backend = event.backend
                    if event.usage:
                        trace.usage.append(event.usage)
                    continue
                if len(trace.llm_ttft_ms) <= step:
                    trace.llm_ttft_ms.append(round((time.monotonic() - start) * 1000))
                if isinstance(event, TextDelta):
                    text += event.text
                    yield Speak(event.text)
                else:
                    calls.append(event)
        if not calls:
            if text.strip():
                conv.add(Message(role="assistant", content=text))
            return
        conv.add(Message(role="assistant", content=text or None, tool_calls=calls))
        async with aclosing(_run_tools(conv, tools, calls, trace)) as tool_events:
            async for event in tool_events:
                yield event
