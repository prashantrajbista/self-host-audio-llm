import httpx

_client: httpx.AsyncClient | None = None


def shared_client() -> httpx.AsyncClient:
    """One pooled client for every outbound HTTP call (LLM, remote STT/TTS), so each turn reuses
    warm TCP/TLS connections instead of paying a fresh handshake per request.
    Generous read timeout (CPU inference can run long), tight connect so a dead service fails fast.
    Pool sized for many concurrent calls: httpx's default of 100 connections would silently queue
    the 101st concurrent LLM stream behind the others."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=180.0, write=30.0, pool=5.0),
            limits=httpx.Limits(max_connections=1000, max_keepalive_connections=200),
        )
    return _client
