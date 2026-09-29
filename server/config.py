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
    whisper_model: str = "small.en"
    tts_voice: str = "af_heart"  # default voice
    # voices a client may pick per session (Kokoro American-English pipeline, lang_code "a")
    tts_voices: list[str] = ["af_heart", "af_bella", "am_michael", "am_fenrir"]

    codec_enabled: bool = False
    device: str = "cpu"
    log_level: str = "INFO"
    vad_threshold: float = 0.5  # silero speech probability cutoff, 0-1

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_voice(settings: Settings, voice: str | None) -> str:
    """Client-requested voice, if allowed; otherwise the configured default."""
    return voice if voice in settings.tts_voices else settings.tts_voice
