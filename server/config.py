from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    stt_backend: str = "faster_whisper"
    llm_backend: str = "ollama"
    tts_backend: str = "kokoro"

    stt_endpoint: str = "http://localhost:8001"
    llm_endpoint: str = "http://localhost:11434"
    tts_endpoint: str = "http://localhost:8002"

    llm_model: str = "llama3.2"
    whisper_model: str = "base.en"
    tts_voice: str = "af_heart"

    codec_enabled: bool = False
    device: str = "cpu"
    log_level: str = "DEBUG"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
