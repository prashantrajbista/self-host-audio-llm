"""Monitoring pieces against fakes, no network: the LLM generation span Langfuse receives (structured input and
output, usage, ids, call name), the own-spans-only filter, and Slack notifications.
Run: python -m tests.test_monitoring
"""

import asyncio
import json

import httpx
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from server import context, notify, telemetry
from server.adapters import http_client
from server.adapters.llm.base import Message
from server.adapters.llm.openai_compat_adapter import OpenAICompatAdapter
from server.config import Settings

SSE = (
    'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
    'data: {"choices":[{"delta":{"content":" there."},"finish_reason":"stop"}]}\n\n'
    'data: {"choices":[],"usage":{"prompt_tokens":12,"completion_tokens":3}}\n\n'
    "data: [DONE]\n\n"
)
slack_posts: list[tuple[str, dict]] = []


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.host == "llm.test":
        return httpx.Response(200, text=SSE)
    slack_posts.append((str(request.url), json.loads(request.read())))
    return httpx.Response(200, text="ok")


async def test_generation_span(exporter: InMemorySpanExporter):
    context.session_id.set("interview-1")
    context.user_id.set("user-1")
    context.llm_call.set("score_answer")
    llm = OpenAICompatAdapter("azure", "https://llm.test/openai", "gpt-4.1-mini", "k")
    with trace.get_tracer("some.library").start_as_current_span("http request"):  # not the app's: filtered out
        events = [e async for e in llm.generate_stream([Message(role="user", content="Grade this.")], temperature=0)]
    assert events
    spans = exporter.get_finished_spans()
    assert [s.name for s in spans] == ["score_answer"], [s.name for s in spans]
    a = spans[0].attributes
    assert a["langfuse.observation.type"] == "generation" and a["gen_ai.request.model"] == "gpt-4.1-mini"
    assert json.loads(a["langfuse.observation.input"]) == [{"role": "user", "content": "Grade this."}]
    assert json.loads(a["langfuse.observation.output"]) == {"role": "assistant", "content": "Hello there."}
    assert json.loads(a["langfuse.observation.usage_details"]) == {"input": 12, "output": 3}
    assert a["langfuse.session.id"] == "interview-1" and a["langfuse.user.id"] == "user-1"
    assert json.loads(a["langfuse.observation.model.parameters"]) == {"temperature": 0}
    assert "langfuse.observation.completion_start_time" in a
    assert a["langfuse.trace.name"] == "score_answer"  # first of the app's spans in this trace: names it

    # inside an interview the LLM call is a child and leaves the trace name to the interview
    exporter.clear()
    context.llm_call.set("interviewer")
    with telemetry.span("interview"):
        [e async for e in llm.generate_stream([Message(role="user", content="Hi")])]
    child, root = exporter.get_finished_spans()
    assert root.attributes["langfuse.trace.name"] == "interview" and "langfuse.trace.name" not in child.attributes
    assert child.parent.span_id == root.context.span_id
    print("generation span PASS")


async def test_notify():
    notify.get_settings = lambda: Settings(slack_webhook_url="https://hooks.test/activity", slack_alerts_webhook_url="https://hooks.test/alerts")
    notify.notify("New purchase")
    notify.notify("Scoring failed", critical=True)
    await asyncio.sleep(0.05)
    assert ("https://hooks.test/activity", {"text": "New purchase"}) in slack_posts, slack_posts
    assert ("https://hooks.test/alerts", {"text": "<!channel> Scoring failed"}) in slack_posts, slack_posts
    notify.get_settings = lambda: Settings(slack_webhook_url="")
    slack_posts.clear()
    notify.notify("nobody listening")
    await asyncio.sleep(0.05)
    assert not slack_posts
    print("notify PASS")


async def main():
    http_client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(telemetry.OwnSpansOnly(SimpleSpanProcessor(exporter)))
    trace.set_tracer_provider(provider)
    telemetry._settings = Settings(langfuse_capture_content=True, environment="test")
    await test_generation_span(exporter)
    await test_notify()


if __name__ == "__main__":
    asyncio.run(main())
