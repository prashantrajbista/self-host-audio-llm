from server.adapters.llm.base import LLMAdapter
from server.adapters.stt.base import STTAdapter
from server.adapters.tts.base import TTSAdapter
from server.config import Settings

# Adapters hold no per-connection state, so cache them as process-wide singletons keyed by their own
# config. STT/TTS are expensive to construct (model load / HF download) — reloading per WS connection
# blocked the event loop long enough to time out the handshake itself. The LLM adapter is shared so its
# fallback circuit-breaker state is process-wide. Settings itself isn't hashable, so key on the
# relevant fields rather than lru_cache-ing the Settings object directly.
_stt_cache: dict[tuple, STTAdapter] = {}
_tts_cache: dict[tuple, TTSAdapter] = {}
_llm_cache: dict[tuple, LLMAdapter] = {}


def get_stt(settings: Settings) -> STTAdapter:
    if settings.stt_backend == "faster_whisper":
        device = settings.device if settings.device != "mps" else "cpu"
        key = ("faster_whisper", settings.whisper_model, device, settings.stt_workers, settings.stt_cpu_threads)
        if key not in _stt_cache:
            from server.adapters.stt.faster_whisper_adapter import FasterWhisperAdapter

            _stt_cache[key] = FasterWhisperAdapter(
                model_size=settings.whisper_model,
                device=device,
                workers=settings.stt_workers,
                cpu_threads=settings.stt_cpu_threads,
            )
        return _stt_cache[key]
    if settings.stt_backend == "remote":
        key = ("remote", settings.stt_endpoint)
        if key not in _stt_cache:
            from server.adapters.stt.http_client_adapter import HTTPSTTAdapter

            _stt_cache[key] = HTTPSTTAdapter(endpoint=settings.stt_endpoint)
        return _stt_cache[key]
    raise ValueError(f"Unknown STT_BACKEND: {settings.stt_backend}")


def get_llm(settings: Settings) -> LLMAdapter:
    """OpenAI, vLLM and Ollama all speak the OpenAI-compatible API; LLM_BACKEND is just the primary's label.
    Stateless (cancel = close the stream), so one instance serves every session."""
    key = (
        settings.llm_backend, settings.llm_endpoint, settings.llm_model, settings.openai_api_key,
        settings.llm_fallback_endpoint, settings.llm_fallback_model, settings.llm_fallback_api_key,
        settings.llm_first_token_timeout,
    )
    if key not in _llm_cache:
        from server.adapters.llm.fallback import FallbackLLM
        from server.adapters.llm.openai_compat_adapter import OpenAICompatAdapter

        backends: list[LLMAdapter] = [
            OpenAICompatAdapter(settings.llm_backend, settings.llm_endpoint, settings.llm_model, settings.openai_api_key)
        ]
        if settings.llm_fallback_endpoint:
            backends.append(
                OpenAICompatAdapter(
                    "fallback",
                    settings.llm_fallback_endpoint,
                    settings.llm_fallback_model or settings.llm_model,
                    settings.llm_fallback_api_key,
                )
            )
        _llm_cache[key] = FallbackLLM(backends, first_event_timeout=settings.llm_first_token_timeout)
    return _llm_cache[key]


def get_tts(settings: Settings) -> TTSAdapter:
    if settings.tts_backend == "kokoro":
        voices = tuple(settings.tts_voices)
        key = ("kokoro", settings.tts_voice, voices, settings.device, settings.tts_speed, settings.tts_workers)
        if key not in _tts_cache:
            from server.adapters.tts.kokoro_adapter import KokoroAdapter

            _tts_cache[key] = KokoroAdapter(
                voice=settings.tts_voice,
                device=settings.device,
                voices=voices,
                speed=settings.tts_speed,
                workers=settings.tts_workers,
            )
        return _tts_cache[key]
    if settings.tts_backend == "remote":
        key = ("remote", settings.tts_endpoint)
        if key not in _tts_cache:
            from server.adapters.tts.http_client_adapter import HTTPTTSAdapter

            _tts_cache[key] = HTTPTTSAdapter(endpoint=settings.tts_endpoint)
        return _tts_cache[key]
    raise ValueError(f"Unknown TTS_BACKEND: {settings.tts_backend}")
