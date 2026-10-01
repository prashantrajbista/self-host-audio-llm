"""Dropped interview calls: a reconnect resumes the same interview, a hang-up or timeout finishes it.
Fake socket and adapters, no models or database. Run: python -m tests.test_resume
"""

import asyncio
import random

from server.agent.interview import Interview, load_packs, plan_questions
from server.gateway import ws_handler
from server.gateway.session import VoiceSession
from tests.test_session import FakeLLM, FakeSTT, FakeTTS, FakeVAD

SID = "00000000-0000-0000-0000-000000000001"


class FakeWS:
    def __init__(self, token="t"):
        self.query_params = {"session_id": SID, "token": token}
        self.client = None
        self.sent: list[dict] = []
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.closed_with = None

    async def accept(self):
        pass

    async def close(self, code=1000, reason=""):
        self.closed_with = code

    async def send_json(self, msg):
        self.sent.append(msg)

    async def send_bytes(self, _):
        pass

    async def receive(self):
        return await self.inbox.get()

    def drop(self, code=1006):
        self.inbox.put_nowait({"type": "websocket.disconnect", "code": code})


async def main():
    pack = load_packs("packs")["tech_behavioral"]
    starts, finished = [], []

    async def start(params, uid, settings, emit):
        starts.append(uid)
        return Interview(pack, plan_questions(pack, "behavioral", "junior", random.Random(0)), "Engineer", "junior", "behavioral", emit), 0

    async def finish(settings, session_id, record):
        finished.append(record)

    async def verify(settings, token):
        return {"t": "alice", "m": "mallory"}.get(token)

    def new_session(ws, settings, agent):
        return VoiceSession(FakeSTT(), FakeLLM(), FakeTTS(), FakeVAD(), ws.send_json, ws.send_bytes, agent=agent)

    ws_handler._start_interview = start
    ws_handler._finish_interview = finish
    ws_handler.verify_token = verify
    ws_handler._new_session = new_session
    ws_handler.RESUME_WINDOW_S = 0.3

    # drop, then reconnect: same interview, not charged again, the old turns are kept
    first = FakeWS()
    t1 = asyncio.create_task(ws_handler.websocket_endpoint(first))
    await asyncio.sleep(0.2)
    call = ws_handler._live[SID]
    first.drop()
    await t1
    assert SID in ws_handler._parked and not finished
    stranger = FakeWS("m")
    ws_handler._start_interview = lambda *a: _refuse()
    await ws_handler.websocket_endpoint(stranger)
    assert SID in ws_handler._parked, "someone else can't take over the call"

    second = FakeWS()
    t2 = asyncio.create_task(ws_handler.websocket_endpoint(second))
    await asyncio.sleep(0.2)
    assert ws_handler._live[SID] is call and SID not in ws_handler._parked
    assert starts == ["alice"], starts
    assert any(m["type"] == "state" for m in second.sent), "resumed session talks to the new socket"

    # reconnect while the old connection hasn't noticed it's dead: the new one takes over
    third = FakeWS()
    t3 = asyncio.create_task(ws_handler.websocket_endpoint(third))
    await asyncio.sleep(0.2)
    await t2
    assert ws_handler._live[SID] is call and not finished

    # hang-up finishes right away
    third.drop(1000)
    await t3
    await asyncio.sleep(0.05)
    assert len(finished) == 1 and SID not in ws_handler._parked and SID not in ws_handler._live
    print("resume + takeover + hang-up PASS")

    # drop with no reconnect: finished after the window
    finished.clear()
    ws_handler._start_interview = start
    fourth = FakeWS()
    t4 = asyncio.create_task(ws_handler.websocket_endpoint(fourth))
    await asyncio.sleep(0.2)
    fourth.drop()
    await t4
    assert not finished
    await asyncio.sleep(0.5)
    assert len(finished) == 1 and SID not in ws_handler._parked
    print("timeout PASS")


async def _refuse():
    return None, ws_handler.POLICY_CLOSE_CODE


if __name__ == "__main__":
    asyncio.run(main())
