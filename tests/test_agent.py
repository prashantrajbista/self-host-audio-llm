"""Agentic core checks with a scripted fake LLM (no models, no network).
Run: python -m tests.test_agent
"""

import asyncio
import time

from server.adapters.llm.base import Done, LLMAdapter, Message, TextDelta, ToolCall
from server.adapters.llm.fallback import FAILURE_THRESHOLD, FallbackLLM
from server.agent import loop
from server.agent.agents import AgentDef
from server.agent.conversation import MAX_MESSAGES, Conversation
from server.agent.loop import CONFIRM_REQUIRED, Filler, Prefetch, Speak, ToolFinished, ToolStarted, TurnTrace, run_turn
from server.agent.tools import MAX_RESULT_CHARS, execute, tool


class ScriptedLLM(LLMAdapter):
    """Each generate_stream call plays the next scripted step; records what it was sent."""

    def __init__(self, steps, delay=0.0):
        self.steps = list(steps)
        self.delay = delay
        self.requests = []
        self.params = []
        self.closed = 0  # streams closed before finishing (aborted requests)

    async def generate_stream(self, messages, tools=None, **params):
        self.requests.append((list(messages), tools))
        self.params.append(params)
        try:
            for event in self.steps.pop(0):
                await asyncio.sleep(self.delay)
                yield event
            yield Done("stop", None, "fake")
        except (asyncio.CancelledError, GeneratorExit):
            self.closed += 1
            raise


def text(s):
    words = s.split(" ")
    return [TextDelta(words[0])] + [TextDelta(" " + w) for w in words[1:]]


@tool
async def add(a: int, b: int) -> str:
    """Add two numbers.

    Args:
        a: first number
        b: second number
    """
    return str(a + b)


@tool(timeout=0.05)
async def slow(x: str = "y") -> str:
    """Too slow."""
    await asyncio.sleep(1)
    return "never"


@tool(filler="Hang on.")
async def wait(seconds: float) -> str:
    """Sleep."""
    await asyncio.sleep(seconds)
    return "waited"


@tool
async def big() -> str:
    """Huge output."""
    return "x" * (MAX_RESULT_CHARS * 2)


BOOKED = []


@tool(side_effect=True)
async def book(day: str) -> str:
    """Book something."""
    await asyncio.sleep(0.05)
    BOOKED.append(day)
    return f"booked {day}"


AGENT = AgentDef(name="t", tools=(add, slow, wait, big, book))


async def collect(conv, agent, llm, prefetch=None):
    trace = TurnTrace()
    events = [e async for e in run_turn(conv, agent, llm, trace, prefetch)]
    return events, trace


def spoken(events):
    return "".join(e.text for e in events if isinstance(e, Speak))


async def test_tools():
    assert add.parameters == {
        "type": "object",
        "properties": {"a": {"type": "integer", "description": "first number"}, "b": {"type": "integer", "description": "second number"}},
        "required": ["a", "b"],
    }, add.parameters
    assert slow.parameters["required"] == []
    try:
        tool(lambda: None)
        raise AssertionError("sync tool accepted")
    except TypeError:
        pass
    assert await execute(add, '{"a": 2, "b": 3}') == "5"
    assert (await execute(add, "not json")).startswith("Error: invalid arguments")
    assert (await execute(add, '{"a": 1}')).startswith("Error: bad arguments")
    assert "timed out" in await execute(slow, "{}")
    assert len(await execute(big, "{}")) < MAX_RESULT_CHARS + 20
    print("tool schema + execution PASS")


async def test_plain_reply_and_memory():
    conv = Conversation()
    conv.add_user("hi")
    llm = ScriptedLLM([text("Hello there."), text("You said hi.")])
    events, trace = await collect(conv, AgentDef(name="plain"), llm)
    assert spoken(events) == "Hello there.", spoken(events)
    assert conv.messages[-1].content == "Hello there."
    assert llm.requests[0][1] is None, "agent without tools must not send tools"
    conv.add_user("what did I say")
    await collect(conv, AgentDef(name="plain"), llm)
    sent = llm.requests[1][0]
    assert [m.role for m in sent] == ["system", "user", "assistant", "user"], [m.role for m in sent]
    assert trace.backend == "fake" and len(trace.llm_ttft_ms) == 1
    print("plain reply + conversation memory PASS")


async def test_parallel_tools_and_filler():
    conv = Conversation()
    conv.add_user("add and wait")
    llm = ScriptedLLM([
        text("Let me check.") + [ToolCall("c1", "add", '{"a": 1, "b": 2}'), ToolCall("c2", "wait", '{"seconds": 0.6}')],
        text("Three."),
    ])
    start = time.monotonic()
    events, trace = await collect(conv, AGENT, llm)
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, f"tools not parallel: {elapsed:.2f}s"
    assert [e.name for e in events if isinstance(e, ToolStarted)] == ["add", "wait"]
    assert [e.text for e in events if isinstance(e, Filler)] == ["Hang on."], events
    assert all(e.ok for e in events if isinstance(e, ToolFinished))
    roles = [m.role for m in conv.messages]
    assert roles == ["user", "assistant", "tool", "tool", "assistant"], roles
    assert conv.messages[2].content == "3" and conv.messages[2].tool_call_id == "c1"
    assert len(trace.tools) == 2 and len(trace.llm_ttft_ms) == 2
    # fast tools add no filler
    conv2 = Conversation()
    conv2.add_user("add")
    events, _ = await collect(conv2, AGENT, ScriptedLLM([[ToolCall("c1", "add", '{"a": 1, "b": 1}')], text("Two.")]))
    assert not any(isinstance(e, Filler) for e in events)
    print("parallel tools + filler PASS")


async def test_max_steps():
    conv = Conversation()
    conv.add_user("loop forever")
    agent = AgentDef(name="m", tools=(add,), max_steps=3)
    call = [ToolCall("c", "add", '{"a": 1, "b": 1}')]
    llm = ScriptedLLM([call, call, text("Done.")])
    events, _ = await collect(conv, agent, llm)
    assert [tools for _, tools in llm.requests][-1] is None, "last step must be sent without tools"
    assert llm.requests[0][1] is not None
    assert "Done." in spoken(events)
    print("max steps PASS")


async def test_confirmation():
    BOOKED.clear()
    conv = Conversation()
    conv.add_user("book monday")
    call = [ToolCall("c1", "book", '{"day": "monday"}')]
    await collect(conv, AGENT, ScriptedLLM([call, text("Confirm monday?")]))
    assert BOOKED == [] and conv.messages[2].content == CONFIRM_REQUIRED
    conv.add_user("yes")
    await collect(conv, AGENT, ScriptedLLM([[ToolCall("c2", "book", '{"day": "monday"}')], text("Booked.")]))
    assert BOOKED == ["monday"], BOOKED
    # same call again in the same turn: confirmation already consumed, so not executed twice
    await collect(conv, AGENT, ScriptedLLM([[ToolCall("c3", "book", '{"day": "monday"}')], text("Hm.")]))
    assert BOOKED == ["monday"], BOOKED
    # different args than what was confirmed: not executed
    conv.add_user("yes")
    await collect(conv, AGENT, ScriptedLLM([[ToolCall("c4", "book", '{"day": "friday"}')], text("Confirm friday?")]))
    assert BOOKED == ["monday"], BOOKED
    print("side-effect confirmation PASS")


async def test_barge_in_during_tools():
    BOOKED.clear()
    conv = Conversation()
    conv.add_user("book tuesday")
    conv.pending_confirmations[("book", '{"day": "tuesday"}')] = 0  # confirmed last turn
    llm = ScriptedLLM([[ToolCall("c1", "book", '{"day": "tuesday"}'), ToolCall("c2", "wait", '{"seconds": 5}')], text("x")])
    task = asyncio.create_task(collect(conv, AGENT, llm))
    await asyncio.sleep(0.02)
    task.cancel()
    await asyncio.wait([task])
    results = {m.tool_call_id: m.content for m in conv.messages if m.role == "tool"}
    assert set(results) == {"c1", "c2"}, "every tool call needs a result message"
    assert results["c2"].startswith("Cancelled")
    assert results["c1"].startswith("Still running")
    await asyncio.sleep(0.1)  # side-effecting tool finishes anyway and reports back
    assert BOOKED == ["tuesday"]
    conv.add_user("hello?")
    assert "book finished: booked tuesday" in conv.messages[-1].content, conv.messages[-1].content
    print("barge-in during tools PASS")


def test_interrupt_and_trim():
    conv = Conversation()
    conv.add_user("tell me a story")
    conv.add(Message(role="assistant", content="Let me think.", tool_calls=[ToolCall("c", "add", "{}")]))
    conv.add(Message(role="tool", content="2", tool_call_id="c"))
    conv.add(Message(role="assistant", content="Once upon a time there was a very long story."))
    conv.mark_interrupted("Once upon a time ")
    assert [m.role for m in conv.messages] == ["user", "assistant", "tool", "assistant"]
    assert conv.messages[1].content is None and conv.messages[1].tool_calls
    assert conv.messages[-1].content == "Once upon a time"
    conv.add_user("stop")
    assert "interrupted" in conv.messages[-1].content
    # unanswered user turn followed by another: merged, roles keep alternating
    conv.add_user("hello")
    assert conv.messages[-1].content.endswith("stop\nhello") and conv.messages[-2].role == "assistant"

    conv = Conversation()
    for i in range(60):
        conv.add_user(f"u{i}")
        conv.add(Message(role="assistant", content=f"a{i}"))
    assert len(conv.messages) <= MAX_MESSAGES and conv.messages[0].role == "user"
    print("interrupt truncation + trim PASS")


class FailingLLM(LLMAdapter):
    def __init__(self, name, hang=False):
        self.name, self.hang, self.calls = name, hang, 0

    async def generate_stream(self, messages, tools=None, **params):
        self.calls += 1
        if self.hang:
            await asyncio.sleep(10)
        raise RuntimeError("down")
        yield


async def test_prefetch():
    # preview is exactly what add_user leads to, notes and merged user turns included
    conv = Conversation()
    conv.add_user("first")  # unanswered: the next user message merges into it
    conv.add_note("late result")
    preview = conv.preview_messages("sys", "second")
    conv.add_user("second")
    assert preview == conv.request_messages("sys"), (preview, conv.request_messages("sys"))

    # prefetched first step is replayed, not re-requested; tools still run only after commit
    conv = Conversation()
    llm = ScriptedLLM([text("Let me check.") + [ToolCall("c1", "add", '{"a": 2, "b": 2}')], text("Four.")])
    p = Prefetch(llm, AGENT, conv.preview_messages(AGENT.system_prompt, "add"))
    await asyncio.sleep(0.01)
    assert len(llm.requests) == 1 and not conv.messages, "prefetch must not touch the conversation"
    conv.add_user("add")
    events, trace = await collect(conv, AGENT, llm, prefetch=p)
    assert len(llm.requests) == 2, "first step must come from the prefetch"
    assert trace.prefetched and spoken(events) == "Let me check.Four."
    assert conv.messages[2].content == "4"
    assert llm.params[0] == {"max_tokens": 400}, llm.params[0]

    # cancelling an unused prefetch aborts its request
    slow = ScriptedLLM([text("a b c d e f")], delay=0.05)
    p = Prefetch(slow, AGENT, conv.preview_messages(AGENT.system_prompt, "x"))
    await asyncio.sleep(0.02)
    p.cancel()
    await asyncio.sleep(0.01)
    assert slow.closed == 1
    print("speculative prefetch PASS")


async def test_fallback():
    primary, secondary = FailingLLM("primary", hang=True), ScriptedLLM([text("ok")] * 10)
    llm = FallbackLLM([primary, secondary], first_event_timeout=0.05)
    for _ in range(FAILURE_THRESHOLD):
        events = [e async for e in llm.generate_stream([])]
        assert events[-1].backend == "fake"
    calls = primary.calls
    start = time.monotonic()
    [e async for e in llm.generate_stream([])]
    assert primary.calls == calls, "open circuit must skip the primary"
    assert time.monotonic() - start < 0.05, "open circuit must not pay the timeout"
    # single backend: retried once, then the error surfaces
    solo = FailingLLM("solo")
    try:
        [e async for e in FallbackLLM([solo], 0.05).generate_stream([])]
        raise AssertionError("expected failure")
    except RuntimeError:
        assert solo.calls == 2
    print("fallback + circuit breaker PASS")


async def test_concurrency(n=200):
    """Many concurrent sessions through the loop: the harness itself must not be the bottleneck."""
    lags = []

    async def probe():
        while True:
            t = time.monotonic()
            await asyncio.sleep(0.01)
            lags.append(time.monotonic() - t - 0.01)

    async def one():
        conv = Conversation()
        conv.add_user("add")
        llm = ScriptedLLM([text("Let me check.") + [ToolCall("c", "add", '{"a": 1, "b": 2}')], text("It is three, all good.")], delay=0.005)
        await collect(conv, AGENT, llm)

    p = asyncio.create_task(probe())
    start = time.monotonic()
    await asyncio.gather(*(one() for _ in range(n)))
    elapsed = time.monotonic() - start
    p.cancel()
    worst = max(lags) * 1000
    assert worst < 50, f"event loop lag {worst:.1f}ms"
    print(f"concurrency PASS: {n} sessions in {elapsed:.2f}s, worst loop lag {worst:.1f}ms")


async def main():
    loop.FILLER_DELAY_S = 0.2
    await test_tools()
    await test_plain_reply_and_memory()
    await test_parallel_tools_and_filler()
    await test_max_steps()
    await test_confirmation()
    await test_barge_in_during_tools()
    test_interrupt_and_trim()
    await test_prefetch()
    await test_fallback()
    await test_concurrency()


if __name__ == "__main__":
    asyncio.run(main())
