"""LLM tracing, error reports, and optional traces/metrics. Built on open standards so each backend is a config value:
Langfuse via its OpenTelemetry (OTLP) endpoint for LLM calls, Sentry's DSN for errors, and any OTLP backend for the rest.
Everything here is a no-op until its setting is filled in (server/config.py)."""

import asyncio
import base64
import json
import logging
from datetime import UTC, datetime

from opentelemetry import metrics, trace
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.trace import Status, StatusCode

from server import context
from server.config import Settings

logger = logging.getLogger(__name__)

SCOPE = "voicewire"  # the app's own spans; only these go to Langfuse (not HTTP/DB instrumentation)
_tracer = trace.get_tracer(SCOPE)
_meter = metrics.get_meter(SCOPE)
_settings: Settings | None = None

# instruments exist from import (proxied to the real provider once setup() runs, no-ops otherwise)
active_calls = _meter.create_up_down_counter("voice.calls.active", description="Live voice calls")
turn_latency = _meter.create_histogram("voice.turn.first_audio", unit="ms", description="End of speech to first reply audio")
turn_errors = _meter.create_counter("voice.turn.errors", description="Turns that failed (STT, LLM or TTS)")
interviews = _meter.create_counter("interviews.finished", description="Finished interviews by outcome")
refunds = _meter.create_counter("interviews.refunded", description="Credits given back for failed or empty interviews")


def setup(app, settings: Settings) -> None:
    global _settings
    _settings = settings
    if settings.sentry_dsn:
        import sentry_sdk

        # errors only: performance tracing is OpenTelemetry's job. logger.error/exception become Sentry events.
        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment, traces_sample_rate=0, send_default_pii=False)
    if not (settings.otel_endpoint or _langfuse_on(settings)):
        return

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.name": "voicewire-gateway", "deployment.environment": settings.environment})
    provider = TracerProvider(resource=resource)
    if settings.otel_endpoint:
        headers = dict(kv.split("=", 1) for kv in settings.otel_headers.split(",") if "=" in kv)
        endpoint = settings.otel_endpoint.rstrip("/")
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces", headers=headers)))

        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics", headers=headers))
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))
    if _langfuse_on(settings):
        auth = base64.b64encode(f"{settings.langfuse_public_key}:{settings.langfuse_secret_key}".encode()).decode()
        exporter = OTLPSpanExporter(
            endpoint=f"{settings.langfuse_base_url.rstrip('/')}/api/public/otel/v1/traces",
            headers={"Authorization": f"Basic {auth}", "x-langfuse-ingestion-version": "4"},
        )
        provider.add_span_processor(OwnSpansOnly(BatchSpanProcessor(exporter)))
    trace.set_tracer_provider(provider)
    # the call itself is traced as an "interview" span (ws_handler); health checks are noise
    FastAPIInstrumentor.instrument_app(app, excluded_urls="ws,health")
    HTTPXClientInstrumentor().instrument()


def _langfuse_on(settings: Settings) -> bool:
    return bool(settings.langfuse_base_url and settings.langfuse_public_key and settings.langfuse_secret_key)


class OwnSpansOnly(SpanProcessor):
    """Span processor wrapper: pass on only the app's own spans, so Langfuse sees interviews and LLM calls, not
    every HTTP request."""

    def __init__(self, inner):
        self._inner = inner

    def on_start(self, span, parent_context=None):
        pass

    def on_end(self, span):
        if span.instrumentation_scope and span.instrumentation_scope.name == SCOPE:
            self._inner.on_end(span)

    def shutdown(self):
        self._inner.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self._inner.force_flush(timeout_millis)


def identify(session_id: str | None = None, user_id: str | None = None) -> None:
    """Attach the interview / user to everything that follows in this task: logs, spans, Sentry events."""
    if session_id:
        context.session_id.set(session_id)
    if user_id:
        context.user_id.set(user_id)
    if _settings and _settings.sentry_dsn:
        import sentry_sdk

        if session_id:
            sentry_sdk.set_tag("interview_id", session_id)
        if user_id:
            sentry_sdk.set_user({"id": user_id})
    span = trace.get_current_span()
    for key, value in (("langfuse.session.id", session_id), ("langfuse.user.id", user_id)):
        if value:
            span.set_attribute(key, value)


def _trace_attrs(name: str) -> dict:
    """Langfuse trace-level attributes. The trace name only from a span that starts the app's part of the trace:
    an LLM call inside an interview must not rename the interview's trace."""
    attrs = {"langfuse.environment": _settings.environment if _settings else "development"}
    parent = trace.get_current_span()
    scope = getattr(parent, "instrumentation_scope", None)
    if not (scope and scope.name == SCOPE):
        attrs["langfuse.trace.name"] = name
    if sid := context.session_id.get():
        attrs["langfuse.session.id"] = sid
    if uid := context.user_id.get():
        attrs["langfuse.user.id"] = uid
    return attrs


def span(name: str, **attrs):
    """A span of the app's own (a context manager), carrying the current interview and user for Langfuse."""
    return _tracer.start_as_current_span(name, attributes=_trace_attrs(name) | attrs)


def _capture() -> bool:
    return bool(_settings and _settings.langfuse_capture_content)


class Generation:
    """One LLM request as a Langfuse "generation": the messages in, the reply (text + tool calls) out, model,
    parameters, token usage and time to first token. Not made current: it lives across an async generator's yields."""

    def __init__(self, backend: str, model: str, messages: list[dict], params: dict, tools: list[dict] | None):
        name = context.llm_call.get()
        attrs = _trace_attrs(name) | {
            "langfuse.observation.type": "generation",
            "gen_ai.system": "openai",
            "gen_ai.request.model": model,
            "langfuse.observation.model.parameters": json.dumps(params),
            "langfuse.observation.metadata.backend": backend,
        }
        if _capture():
            attrs["langfuse.observation.input"] = json.dumps(
                {"messages": messages, "tools": [t["function"]["name"] for t in tools or []]} if tools else messages
            )
        self._span = _tracer.start_span(name, attributes=attrs)
        self._first = False

    def first_token(self) -> None:
        if not self._first:
            self._first = True
            self._span.set_attribute("langfuse.observation.completion_start_time", datetime.now(UTC).isoformat())

    def end(self, text: str, tool_calls: list[dict], usage: dict | None, error: BaseException | None = None) -> None:
        if _capture():
            out: dict = {"role": "assistant", "content": text}
            if tool_calls:
                out["tool_calls"] = tool_calls
            self._span.set_attribute("langfuse.observation.output", json.dumps(out))
        if usage:
            self._span.set_attribute(
                "langfuse.observation.usage_details",
                json.dumps({"input": usage.get("prompt_tokens", 0), "output": usage.get("completion_tokens", 0)}),
            )
        if isinstance(error, (GeneratorExit, asyncio.CancelledError)):
            # barge-in or a discarded speculative request: expected, not a failure
            self._span.set_attribute("langfuse.observation.level", "DEBUG")
            self._span.set_attribute("langfuse.observation.status_message", "cancelled")
        elif error is not None:
            self._span.set_status(Status(StatusCode.ERROR, str(error)[:300]))
            self._span.record_exception(error)
        self._span.end()

