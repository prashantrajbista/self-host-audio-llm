import os
import secrets
from functools import lru_cache

from pydantic import Field
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
    packs_dir: str = "packs"  # interview packs (packs/*.toml)
    # sqlite+aiosqlite:///path locally; postgresql+asyncpg://... in production. Schema: `uv run alembic upgrade head`
    database_url: str = "sqlite+aiosqlite:///data/app.db"
    # interview grading model (any OpenAI-compatible API); empty fields reuse the LLM_* settings
    scoring_endpoint: str = ""
    scoring_model: str = ""
    scoring_api_key: str = ""
    # auth: Supabase Auth verifies users' access tokens (URL + publishable key)
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_service_role_key: str = ""  # server only, full access: needed for STORAGE_BACKEND=supabase
    # file storage (CVs, recordings): "azure" (Blob Storage), "supabase" (private bucket) or "local" (disk, development)
    storage_backend: str = "local"
    storage_bucket: str = "interview-coach"  # bucket / Azure container name
    azure_storage_connection_string: str = ""  # server only: needed for STORAGE_BACKEND=azure
    local_storage_dir: str = "data/blobs"
    files_secret: str = Field(default_factory=lambda: secrets.token_hex(32))  # signs local file URLs
    public_base_url: str = "http://localhost:8000"  # this gateway as browsers reach it (local file URLs)
    site_url: str = "http://localhost:3000"  # the web app (payment return links)
    # payments: "paddle" (merchant of record, works for Nepal) or "stripe"
    payment_provider: str = "paddle"
    paddle_env: str = "sandbox"  # sandbox | production (separate Paddle accounts, keys and price ids)
    paddle_api_key: str = ""  # server only; permission: Transactions read + write
    paddle_webhook_secret: str = ""  # the notification destination's secret key
    paddle_price_credits_5: str = ""
    paddle_price_pass_30: str = ""
    # Stripe Checkout, one-time prices created in the Stripe dashboard
    stripe_secret_key: str = ""  # server only
    stripe_webhook_secret: str = ""  # whsec_...: verifies /billing/webhook calls really come from Stripe
    stripe_price_credits_5: str = ""
    stripe_price_pass_30: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]  # web client origins allowed to call the HTTP API
    whisper_model: str = "small.en"
    tts_voice: str = "af_heart"  # default voice
    tts_speed: float = 1.15  # Kokoro speaking rate multiplier, 1.0 = normal
    # voices a client may pick per session (Kokoro American-English pipeline, lang_code "a")
    tts_voices: list[str] = ["af_heart", "af_bella", "am_michael", "am_fenrir"]
    # "torch" (kokoro package, CPU or GPU) or "onnx" (kokoro-onnx int8, CPU only, much faster there)
    tts_engine: str = "torch"
    tts_onnx_model: str = "models/kokoro-v1.0.int8.onnx"  # from the kokoro-onnx model-files-v1.0 release
    tts_onnx_voices: str = "models/voices-v1.0.bin"
    tts_onnx_threads: int = 0  # ONNX Runtime threads per sentence; 0 = all cores

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
        env_file = os.getenv("ENV_FILE", ".env.local")  # .env.local for development, .env.production on the server


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_voice(settings: Settings, voice: str | None) -> str:
    """Client-requested voice, if allowed; otherwise the configured default."""
    return voice if voice in settings.tts_voices else settings.tts_voice
