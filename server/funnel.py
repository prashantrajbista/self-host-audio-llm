"""Sign-up funnel by first-touch source: which landing page / channel brings users who practise and pay.

Run: uv run python -m server.funnel
Page visits come from the web analytics; this counts what happens after sign-in."""

import asyncio
from collections import Counter

from sqlalchemy import select

from server.store.db import sessions
from server.store.models import InterviewSession, Payment, Profile

STEPS = ("signed up", "set up a mock", "started a mock", "gave interview date", "paid")


def source(attribution: dict | None) -> str:
    a = attribution or {}
    return f"{a.get('landing') or '?'} · {a.get('utm_source') or a.get('referrer') or 'direct'}"


def funnel(profiles: list[tuple[str, dict | None]], rows: list[tuple[str, str, bool]], payers: set[str]) -> dict[str, Counter]:
    """profiles: (user, attribution); rows: (user, status, has interview date); payers: users with a payment."""
    by_user: dict[str, set[str]] = {}
    for uid, status, dated in rows:
        steps = by_user.setdefault(uid, set())
        steps.add("set up a mock")
        if status != "created":
            steps.add("started a mock")
        if dated:
            steps.add("gave interview date")
    out: dict[str, Counter] = {}
    for uid, attribution in profiles:
        done = by_user.get(uid, set()) | {"signed up"} | ({"paid"} if uid in payers else set())
        out.setdefault(source(attribution), Counter()).update(done)
    return out


async def main() -> None:
    async with sessions()() as db:
        profiles = (await db.execute(select(Profile.user_id, Profile.attribution))).all()
        rows = (await db.execute(select(
            InterviewSession.user_id, InterviewSession.status, InterviewSession.interview_date.is_not(None)
        ))).all()
        payers = set(await db.scalars(select(Payment.user_id)))
    table = funnel([tuple(p) for p in profiles], [tuple(r) for r in rows], payers)
    print("source".ljust(50) + "".join(s.rjust(20) for s in STEPS))
    for src, counts in sorted(table.items(), key=lambda kv: -kv[1]["signed up"]):
        print(src[:49].ljust(50) + "".join(str(counts[s]).rjust(20) for s in STEPS))


if __name__ == "__main__":
    asyncio.run(main())
