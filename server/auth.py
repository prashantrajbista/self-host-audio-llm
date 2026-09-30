"""Who is calling: verify a user's access token with the auth provider (Supabase Auth).

Moving off Supabase Auth = replacing verify_token; nothing else touches the provider."""

from server.adapters.http_client import shared_client
from server.config import Settings


async def verify_token(settings: Settings, token: str) -> str | None:
    """The user id for a valid, unexpired access token; None otherwise (missing, expired, forged)."""
    if not token or not settings.supabase_url:
        return None
    r = await shared_client().get(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
        headers={"apikey": settings.supabase_publishable_key, "Authorization": f"Bearer {token}"},
    )
    return r.json().get("id") if r.status_code == 200 else None
