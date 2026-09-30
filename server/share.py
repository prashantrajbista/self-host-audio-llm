"""Public share cards: the ONLY place that decides what of an interview becomes public.

Stored choices (share_fields) are applied at read time, so a re-scored report updates its card. Never add
transcript, audio, CV, job description or account details here."""

import re

from pydantic import BaseModel, Field

from server.store.models import InterviewSession

BRAND = "VoiceWire Interview"
LEVEL_LABEL = {"junior": "Entry level", "mid": "Mid level", "senior": "Senior"}
MAX_QUOTE_CHARS = 200


class ShareChoices(BaseModel):
    show_name: bool = True
    name: str = Field("", max_length=40)
    show_role: bool = True
    show_skills: bool = True
    show_delivery: bool = True
    show_strength: bool = True
    quote: str | None = Field(None, max_length=MAX_QUOTE_CHARS)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def validate(choices: ShareChoices, report: dict) -> ShareChoices:
    """Raise ValueError unless the quote is really something the candidate said (no made-up claims
    published under the brand). Returns the choices with text trimmed."""
    choices = choices.model_copy(update={"name": choices.name.strip(), "quote": (choices.quote or "").strip() or None})
    if choices.quote:
        said = " ".join(_norm(a.get("answer_text", "")) for a in report.get("answers", []))
        if _norm(choices.quote) not in said:
            raise ValueError("The quote must be something you said in this interview.")
    return choices


def initials(name: str | None) -> str:
    parts = [p for p in re.split(r"\s+", name or "") if p[:1].isalpha()]
    return "".join(p[0].upper() for p in parts[:2]) if parts else ""


def public_card(session: InterviewSession) -> dict:
    report = session.report or {}
    c = ShareChoices(**(session.share_fields or {}))
    d = report.get("delivery") or {}
    card = {
        "brand": BRAND,
        "score": report.get("overall_score"),
        "verdict": report.get("verdict"),
        "date": session.created_at.date().isoformat(),
        "name": c.name if c.show_name and c.name else None,
        "role": session.role if c.show_role else None,
        "level": LEVEL_LABEL.get(session.seniority) if c.show_role else None,
        "skills": report.get("dimensions") if c.show_skills else None,
        "delivery": (
            {"wpm": d.get("wpm"), "fillers_per_min": d.get("fillers_per_min"), "avg_answer_s": d.get("avg_answer_s")}
            if c.show_delivery else None
        ),
        "top_strength": report.get("top_strength") if c.show_strength else None,
        "quote": c.quote,
    }
    return card
