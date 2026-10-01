"""Notifications to the team: purchases, sign-ups, contact messages, refunds and failures.

Backends are picked by NOTIFY_BACKENDS (like STT_BACKEND); add one by writing a `_send_<name>` coroutine.
Sent in the background: a slow or failing webhook never delays the request, and its failure is only logged."""

import asyncio
import logging

from server.adapters.http_client import shared_client
from server.config import get_settings

logger = logging.getLogger(__name__)
_pending: set[asyncio.Task] = set()  # strong refs: a bare create_task can be garbage-collected mid-run


async def _send_slack(text: str, critical: bool) -> None:
    settings = get_settings()
    url = (settings.slack_alerts_webhook_url if critical else "") or settings.slack_webhook_url
    if not url:
        return
    # incoming webhooks take plain text with Slack's own markup; <!channel> pings everyone in the channel
    response = await shared_client().post(url, json={"text": f"<!channel> {text}" if critical else text})
    response.raise_for_status()


_BACKENDS = {"slack": _send_slack}


async def _send(text: str, critical: bool) -> None:
    for name in get_settings().notify_backends:
        try:
            await _BACKENDS[name](text, critical)
        except Exception:
            logger.warning("notification via %s failed", name, exc_info=True)


def notify(text: str, critical: bool = False) -> None:
    """Fire and forget. critical = goes to the alerts channel and pings it."""
    try:
        task = asyncio.get_running_loop().create_task(_send(text, critical))
    except RuntimeError:  # no event loop (a script): nothing to send from
        return
    _pending.add(task)
    task.add_done_callback(_pending.discard)
