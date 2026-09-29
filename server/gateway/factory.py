from server.adapters.llm.base import LLMAdapter
from server.adapters.stt.base import STTAdapter
from server.adapters.tts.base import TTSAdapter
from server.config import Settings

# STT/TTS adapters hold no per-connection state and are expensive to construct (model load /
# HF download), so cache them as process-wide singletons keyed by their own config — reloading
# per WS connection blocked the event loop long enough to time out the handshake itself. LLM
# adapters carry per-connection cancel state (barge-in) and are cheap to build (no model load),
# so those stay fresh per connection. Settings itself isn't hashable, so key on the relevant
# fields rather than lru_cache-ing the Settings object directly.
_stt_cache: dict[tuple, STTAdapter] = {}
_tts_cache: dict[tuple, TTSAdapter] = {}


def get_stt(settings: Settings) -> STTAdapter:
    if settings.stt_backend == "faster_whisper":
        device = settings.device if settings.device != "mps" else "cpu"
        key = ("faster_whisper", settings.whisper_model, device)
        if key not in _stt_cache:
            from server.adapters.stt.faster_whisper_adapter import FasterWhisperAdapter

            _stt_cache[key] = FasterWhisperAdapter(model_size=settings.whisper_model, device=device)
        return _stt_cache[key]
    if settings.stt_backend == "remote":
        key = ("remote", settings.stt_endpoint)
        if key not in _stt_cache:
            from server.adapters.stt.http_client_adapter import HTTPSTTAdapter

            _stt_cache[key] = HTTPSTTAdapter(endpoint=settings.stt_endpoint)
        return _stt_cache[key]
    raise ValueError(f"Unknown STT_BACKEND: {settings.stt_backend}")


def get_llm(settings: Settings) -> LLMAdapter:
    if settings.llm_backend == "ollama":
        from server.adapters.llm.ollama_adapter import OllamaAdapter

        return OllamaAdapter(endpoint=settings.llm_endpoint, model=settings.llm_model)
    if settings.llm_backend == "vllm":
        from server.adapters.llm.vllm_adapter import VLLMAdapter

        return VLLMAdapter(endpoint=settings.llm_endpoint, model=settings.llm_model)
    if settings.llm_backend == "openai":
        from server.adapters.llm.openai_adapter import OpenAIAdapter

        return OpenAIAdapter(endpoint=settings.llm_endpoint, model=settings.llm_model, api_key=settings.openai_api_key)
    raise ValueError(f"Unknown LLM_BACKEND: {settings.llm_backend}")


def get_tts(settings: Settings) -> TTSAdapter:
    if settings.tts_backend == "kokoro":
        voices = tuple(settings.tts_voices)
        key = ("kokoro", settings.tts_voice, voices, settings.device, settings.tts_speed)
        if key not in _tts_cache:
            from server.adapters.tts.kokoro_adapter import KokoroAdapter

            _tts_cache[key] = KokoroAdapter(
                voice=settings.tts_voice, device=settings.device, voices=voices, speed=settings.tts_speed
            )
        return _tts_cache[key]
    if settings.tts_backend == "remote":
        key = ("remote", settings.tts_endpoint)
        if key not in _tts_cache:
            from server.adapters.tts.http_client_adapter import HTTPTTSAdapter

            _tts_cache[key] = HTTPTTSAdapter(endpoint=settings.tts_endpoint)
        return _tts_cache[key]
    raise ValueError(f"Unknown TTS_BACKEND: {settings.tts_backend}")
