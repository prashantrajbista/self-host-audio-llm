"""Interview pack + interviewer checks with fakes (no models, no network).
Run: python -m tests.test_interview
"""

import asyncio
import random
import tempfile
from pathlib import Path

from server.adapters.llm.base import ToolCall
from server.agent.interview import KICKOFF, WRAP_UP, Interview, load_packs, plan_questions
from server.gateway.session import VoiceSession
from tests.test_agent import ScriptedLLM, text
from tests.test_session import SILENCE_FRAME, SPEECH_FRAME, FakeSTT, FakeTTS, FakeVAD


def test_packs():
    pack = load_packs("packs")["tech_behavioral"]
    plan = plan_questions(pack, "behavioral", "junior", random.Random(0))
    assert plan[0]["id"] == "opener" and len(plan) == pack["flow"]["num_questions"], plan
    by_id = {q["id"]: q for q in pack["questions"]}
    assert all("junior" in by_id[q["id"]]["seniority"] and by_id[q["id"]]["type"] == "behavioral" for q in plan[1:])
    assert len({q["id"] for q in plan}) == len(plan), "no repeats"

    with tempfile.TemporaryDirectory() as d:
        Path(d, "bad.toml").write_text('id = "bad"\nname = "x"\n')
        try:
            load_packs(d)
        except ValueError as e:
            assert "missing" in str(e)
        else:
            raise AssertionError("invalid pack should fail to load")
    print("packs PASS")


async def test_question_flow():
    events = []

    async def emit(msg):
        events.append(msg)

    pack = load_packs("packs")["tech_behavioral"]
    iv = Interview(pack, plan_questions(pack, "mixed", "senior"), "SWE", "senior", "mixed", emit)
    for i in range(len(iv.plan)):
        assert (await iv.next_question()).startswith(f"Question {i + 1} of")
    assert await iv.next_question() == WRAP_UP
    assert [e["data"]["index"] for e in events] == list(range(len(iv.plan)))
    assert len(iv.asked_at) == len(iv.plan)

    late = Interview(pack, iv.plan, "SWE", "senior", "mixed", emit)
    late.started_at -= pack["flow"]["duration_min"] * 60 + 1
    assert await late.next_question() == WRAP_UP, "overtime wraps up instead of asking more"

    agent = iv.agent()
    assert {t.name for t in agent.tools} == {"next_question", "end_interview"}
    assert "senior SWE" in agent.system_prompt and "friendly voice assistant" not in agent.system_prompt
    print("question flow PASS")


async def test_session_kickoff_and_turns():
    events = []

    async def send_json(msg):
        events.append(msg)

    async def send_bytes(_):
        pass

    pack = load_packs("packs")["tech_behavioral"]
    iv = Interview(pack, plan_questions(pack, "mixed", "mid"), "SWE", "mid", "mixed", send_json)
    llm = ScriptedLLM([
        [ToolCall("c1", "next_question", "{}")],  # kickoff: fetch the opener
        text("Hi, I'm Alex. Walk me through your background."),
        text("Thanks. Tell me more about your role."),  # reply to the user's answer
    ])
    session = VoiceSession(
        stt=FakeSTT(), llm=llm, tts=FakeTTS(), vad=FakeVAD(),
        send_json=send_json, send_bytes=send_bytes, agent=iv.agent(),
    )
    await session.open(KICKOFF)
    await session.drain()
    assert [e["data"]["index"] for e in events if e["type"] == "question"] == [0]
    assert not any(e["type"] == "partial_transcript" for e in events), "kickoff is hidden"
    assert [t["role"] for t in session.turns] == ["assistant"], session.turns
    assert session.turns[0]["text"].startswith("Hi, I'm Alex")

    for _ in range(8):
        await session.handle_audio_frame(SPEECH_FRAME)
    for _ in range(26):
        await session.handle_audio_frame(SILENCE_FRAME)
    await session.drain()
    roles = [t["role"] for t in session.turns]
    assert roles == ["assistant", "user", "assistant"], session.turns
    user = session.turns[1]
    assert user["text"] == "hello there" and user["start"] < user["end"] <= session.turns[2]["start"] + 1

    record = iv.record(session.turns)
    assert record["questions"][0]["asked_at"] and record["questions"][1]["asked_at"] is None
    print("session kickoff + timed turns PASS")


async def main():
    test_packs()
    await test_question_flow()
    await test_session_kickoff_and_turns()


if __name__ == "__main__":
    asyncio.run(main())
