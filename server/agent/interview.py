"""Mock interview: a pack (packs/*.toml, one per niche) becomes a per-session interviewer agent.

A pack is data only: persona, question bank, flow limits, rubric. Adding a niche = adding a pack file."""

import random
import time
import tomllib
from collections.abc import Awaitable, Callable
from functools import lru_cache
from pathlib import Path

from server.agent.agents import AgentDef
from server.agent.tools import tool

SENIORITIES = ("junior", "mid", "senior")
INTERVIEW_TYPES = ("behavioral", "hr", "mixed")  # mixed = any question type
WRAP_UP = "No more questions. Thank the candidate, tell them their feedback report is being prepared, then call end_interview."
KICKOFF = (
    "The candidate just joined the call. Greet them in one short sentence and introduce yourself, "
    "then call next_question and ask the first question."
)


def _validate(pack: dict, path: Path) -> dict:
    def need(cond: bool, what: str) -> None:
        if not cond:
            raise ValueError(f"invalid pack {path.name}: {what}")

    for key in ("id", "name", "persona", "opener", "flow", "questions", "rubric", "verdicts"):
        need(key in pack, f"missing '{key}'")
    flow = pack["flow"]
    for key in ("num_questions", "max_follow_ups", "duration_min"):
        need(isinstance(flow.get(key), int) and flow[key] >= 0, f"flow.{key} must be a non-negative int")
    need(flow["num_questions"] >= 1, "flow.num_questions must be >= 1")
    ids = [q.get("id") for q in pack["questions"]]
    need(len(ids) == len(set(ids)) and all(ids), "question ids must be present and unique")
    for q in pack["questions"]:
        need(bool(q.get("text")), f"question {q['id']} has no text")
        need(q.get("type") in INTERVIEW_TYPES[:-1], f"question {q['id']} has unknown type {q.get('type')!r}")
        need(set(q.get("seniority") or ()) <= set(SENIORITIES) and bool(q.get("seniority")), f"question {q['id']} has bad seniority")
    need(sum(d.get("weight", 0) for d in pack["rubric"]) > 0, "rubric weights must sum to > 0")
    return pack


@lru_cache
def load_packs(packs_dir: str) -> dict[str, dict]:
    """All packs by id; raises on the first invalid one so a bad pack fails at startup, not mid-call."""
    packs = {}
    for path in sorted(Path(packs_dir).glob("*.toml")):
        pack = _validate(tomllib.loads(path.read_text()), path)
        packs[pack["id"]] = pack
    return packs


def plan_questions(pack: dict, interview_type: str, seniority: str, rng: random.Random | None = None) -> list[dict]:
    """Opener first, then a random draw from the bank matching type and seniority."""
    pool = [
        q for q in pack["questions"]
        if seniority in q["seniority"] and interview_type in (q["type"], "mixed")
    ]
    count = min(pack["flow"]["num_questions"] - 1, len(pool))
    opener = {"id": "opener", "text": pack["opener"]}
    return [opener, *(rng or random).sample(pool, count)]


class Interview:
    """Per-session interview state. The LLM moves through the plan via tools, so question boundaries
    (when each question was handed out) are known server-side for scoring and replay."""

    def __init__(
        self,
        pack: dict,
        plan: list[dict],
        role: str,
        seniority: str,
        interview_type: str,
        emit: Callable[[dict], Awaitable[None]],
    ):
        self.pack = pack
        self.plan = plan
        self.role = role
        self.seniority = seniority
        self.interview_type = interview_type
        self.emit = emit
        self.index = -1
        self.asked_at: list[float] = []  # epoch seconds each plan[i] was handed to the interviewer
        self.started_at = time.time()
        self.ended = False

    def overtime(self) -> bool:
        return time.time() - self.started_at > self.pack["flow"]["duration_min"] * 60

    async def next_question(self) -> str:
        if self.index + 1 >= len(self.plan) or self.overtime():
            return WRAP_UP
        self.index += 1
        self.asked_at.append(time.time())
        text = self.plan[self.index]["text"]
        await self.emit({"type": "question", "data": {"index": self.index, "total": len(self.plan), "text": text}})
        return f"Question {self.index + 1} of {len(self.plan)}: {text}"

    async def end_interview(self) -> str:
        self.ended = True
        return "Interview ended. Say a brief goodbye if you haven't already."

    def agent(self) -> AgentDef:
        @tool(timeout=2.0)
        async def next_question() -> str:
            """Get the next main interview question. Call it to get the first question, and whenever the
            candidate has finished answering the current one, including any follow-ups."""
            return await self.next_question()

        @tool(timeout=2.0)
        async def end_interview() -> str:
            """End the interview. Call it only after next_question says there are no more questions."""
            return await self.end_interview()

        flow = self.pack["flow"]
        kind = "behavioral and HR" if self.interview_type == "mixed" else self.interview_type
        instructions = (
            f"{self.pack['persona'].strip()}\n"
            f"You are interviewing a candidate for a {self.seniority} {self.role} role. This is a {kind} interview "
            f"of {len(self.plan)} questions, about {flow['duration_min']} minutes.\n"
            "How the interview runs:\n"
            "- Get every main question from the next_question tool, including the first. Never invent main questions "
            "or skip ahead. Ask one question at a time, in your own words, conversationally.\n"
            f"- After an answer, ask at most {flow['max_follow_ups']} short follow-up questions, only when it's vague, "
            "lacks specifics, results, or the candidate's own role. Then call next_question.\n"
            "- Don't coach, grade, or give feedback during the interview. Use neutral acknowledgments like \"thanks\" "
            "or \"got it\". The candidate gets a feedback report afterwards.\n"
            "- Don't say \"let me check\" before calling a tool. Transition naturally, like \"Thanks. Next question.\"\n"
            "- If the candidate asks to skip or can't answer, move on with next_question. Answer clarifying questions "
            "briefly without giving away a good answer.\n"
            "- If you were interrupted before finishing a question you already received, ask it again rather than "
            "calling next_question.\n"
            "- When next_question says there are no more questions, thank the candidate, say their feedback report "
            "is being prepared, and call end_interview."
        )
        return AgentDef(
            name=f"interview:{self.pack['id']}",
            instructions=instructions,
            tools=(next_question, end_interview),
            voice=self.pack.get("voice"),
        )

    def record(self, turns: list[dict]) -> dict:
        """Everything scoring (milestone 2) needs: plan, question boundaries, timed turns."""
        return {
            "pack_id": self.pack["id"],
            "role": self.role,
            "seniority": self.seniority,
            "type": self.interview_type,
            "started_at": self.started_at,
            "ended_at": time.time(),
            "completed": self.ended,
            "questions": [
                {**q, "asked_at": self.asked_at[i] if i < len(self.asked_at) else None} for i, q in enumerate(self.plan)
            ],
            "turns": turns,
        }
