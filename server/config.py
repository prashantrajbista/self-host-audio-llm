from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    stt_backend: str = "faster_whisper"
    llm_backend: str = "openai"
    tts_backend: str = "kokoro"

    stt_endpoint: str = "http://localhost:8001"
    llm_endpoint: str = "https://api.openai.com"
    tts_endpoint: str = "http://localhost:8002"

    llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    llm_first_token_timeout: float = 15.0  # s before retry/failover; ~2-3 when a fallback backend is set
    # optional secondary LLM (self-host <-> API either way); empty endpoint disables it
    llm_fallback_endpoint: str = ""
    llm_fallback_model: str = ""
    llm_fallback_api_key: str = ""
    agent: str = "assistant"  # default agent definition (server/agent/agents.py), per-session ?agent= overrides
    packs_dir: str = "packs"  # interview packs (packs/*.toml); a session with ?pack= runs a mock interview
    interviews_dir: str = "data/interviews"  # finished interview records (local JSON until Supabase)
    whisper_model: str = "small.en"
    tts_voice: str = "af_heart"  # default voice
    tts_speed: float = 1.15  # Kokoro speaking rate multiplier, 1.0 = normal
    # voices a client may pick per session (Kokoro American-English pipeline, lang_code "a")
    tts_voices: list[str] = ["af_heart", "af_bella", "am_michael", "am_fenrir"]

    # parallelism of the shared models: each worker is one more utterance/sentence in flight at once
    stt_workers: int = 2  # faster-whisper num_workers
    stt_cpu_threads: int = 0  # threads per STT worker on CPU; 0 = cores / workers
    tts_workers: int = 2  # Kokoro pipelines in the pool (~330MB each)
    max_sessions: int = 50  # concurrent calls per gateway process; extra calls are refused with close code 1013

    codec_enabled: bool = False
    device: str = "cpu"
    log_level: str = "INFO"
    vad_threshold: float = 0.35  # silero speech probability cutoff, 0-1

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_voice(settings: Settings, voice: str | None) -> str:
    """Client-requested voice, if allowed; otherwise the configured default."""
    return voice if voice in settings.tts_voices else settings.tts_voice
