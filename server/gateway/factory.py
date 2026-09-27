from server.adapters.llm.base import LLMAdapter
from server.adapters.stt.base import STTAdapter
from server.adapters.tts.base import TTSAdapter
from server.config import Settings


def get_stt(settings: Settings) -> STTAdapter:
    if settings.stt_backend == "faster_whisper":
        from server.adapters.stt.faster_whisper_adapter import FasterWhisperAdapter

        return FasterWhisperAdapter(model_size=settings.whisper_model, device=settings.device if settings.device != "mps" else "cpu")
    if settings.stt_backend == "remote":
        from server.adapters.stt.http_client_adapter import HTTPSTTAdapter

        return HTTPSTTAdapter(endpoint=settings.stt_endpoint)
    raise ValueError(f"Unknown STT_BACKEND: {settings.stt_backend}")


def get_llm(settings: Settings) -> LLMAdapter:
    if settings.llm_backend == "ollama":
        from server.adapters.llm.ollama_adapter import OllamaAdapter

        return OllamaAdapter(endpoint=settings.llm_endpoint, model=settings.llm_model)
    if settings.llm_backend == "vllm":
        from server.adapters.llm.vllm_adapter import VLLMAdapter

        return VLLMAdapter(endpoint=settings.llm_endpoint, model=settings.llm_model)
    raise ValueError(f"Unknown LLM_BACKEND: {settings.llm_backend}")


def get_tts(settings: Settings) -> TTSAdapter:
    if settings.tts_backend == "kokoro":
        from server.adapters.tts.kokoro_adapter import KokoroAdapter

        return KokoroAdapter(voice=settings.tts_voice)
    if settings.tts_backend == "remote":
        from server.adapters.tts.http_client_adapter import HTTPTTSAdapter

        return HTTPTTSAdapter(endpoint=settings.tts_endpoint)
    raise ValueError(f"Unknown TTS_BACKEND: {settings.tts_backend}")
