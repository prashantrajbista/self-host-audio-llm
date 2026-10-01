"""A candidate who goes quiet: escalating nudges, none while muted or after asking for time, idle end.
Fake adapters and socket, shortened timings, no models. Run: python -m tests.test_silence
"""

import asyncio
import random
import time

from server.agent.interview import Interview, load_packs, plan_questions
from server.gateway import ws_handler
from server.gateway.session import VoiceSession
from tests.test_resume import FakeWS
from tests.test_session import SPEECH_FRAME, FakeLLM, FakeSTT, FakeTTS, FakeVAD


def setup():
    pack = load_packs("packs")["tech_behavioral"]
    ws = FakeWS()
    interview = Interview(pack, plan_questions(pack, "behavioral", "junior", random.Random(0)), "Engineer", "junior", "behavioral", ws.send_json)
    llm = FakeLLM(delay=0)
    session = VoiceSession(FakeSTT(), llm, FakeTTS(), FakeVAD(), ws.send_json, ws.send_bytes, agent=interview.agent())
    return ws, interview, session, llm


def silences(ws):
    return [m["data"] for m in ws.sent if m["type"] == "silence"]


async def main():
    ws_handler.NUDGES = tuple((0.3, text) for _, text in ws_handler.NUDGES)
    ws_handler.IDLE_END_S = 2.0

    # silent candidate: three nudges, then the call ends as idle
    ws, interview, session, llm = setup()
    await asyncio.wait_for(ws_handler._watch_interview(ws, session, interview, "id"), 10)
    assert silences(ws) == [{"muted": False}] * 3, silences(ws)
    assert llm.calls == 4, llm.calls  # 3 nudges + the closing line
    assert interview.idle and interview.ended
    assert ws.sent[-1] == {"type": "interview_end", "data": {"id": "id", "completed": False}}, ws.sent[-1]
    print("nudges + idle end PASS")

    # muted: the client is told, the interviewer stays quiet
    ws, interview, session, llm = setup()
    session.muted = True
    await asyncio.wait_for(ws_handler._watch_interview(ws, session, interview, "id"), 10)
    assert silences(ws) == [{"muted": True}] * 3 and llm.calls == 1, (silences(ws), llm.calls)
    print("muted PASS")

    # speaking starts the nudges over; asking for time holds them off
    ws, interview, session, llm = setup()
    interview.quiet_until = time.time() + 0.8
    watcher = asyncio.create_task(ws_handler._watch_interview(ws, session, interview, "id"))
    await asyncio.sleep(0.7)
    assert not silences(ws), "no nudge while the candidate asked for time"
    await asyncio.sleep(0.6)
    assert len(silences(ws)) == 1, silences(ws)
    await session.handle_audio_frame(SPEECH_FRAME)  # a sound from the candidate
    await asyncio.sleep(1.2)  # the watcher checks every 0.5s
    assert len(silences(ws)) == 2, "a fresh silence after speech is nudged again"
    assert llm.calls == 2 and not interview.idle, (llm.calls, interview.idle)
    watcher.cancel()
    print("give_time + speech PASS")


if __name__ == "__main__":
    asyncio.run(main())
