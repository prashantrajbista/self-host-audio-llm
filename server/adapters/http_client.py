import httpx

_client: httpx.AsyncClient | None = None


def shared_client() -> httpx.AsyncClient:
    """One pooled client for every outbound HTTP call (LLM, remote STT/TTS), so each turn reuses
    warm TCP/TLS connections instead of paying a fresh handshake per request.
    Generous read timeout (CPU inference can run long), tight connect so a dead service fails fast."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=180.0, write=30.0, pool=5.0))
    return _client
