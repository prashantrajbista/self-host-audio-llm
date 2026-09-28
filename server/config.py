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
    whisper_model: str = "base.en"
    tts_voice: str = "af_heart"

    codec_enabled: bool = False
    device: str = "cpu"
    log_level: str = "DEBUG"
    vad_threshold: float = 0.5  # silero speech probability cutoff, 0-1

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
