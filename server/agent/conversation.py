from dataclasses import replace

from server.adapters.llm.base import Message

MAX_MESSAGES = 40  # history cap (excluding system prompt); bounds prefill cost per request
TRIM_BLOCK = 12  # trim this many at once so the cached prompt prefix survives most turns


class Conversation:
    """Per-session history. Plain data, so it can later move to Redis for cross-node failover.

    Notes (interruptions, late outcomes of side-effecting tools) are prefixed to the next user
    message rather than inserted as mid-conversation system messages, which some chat templates reject."""

    def __init__(self) -> None:
        self.messages: list[Message] = []
        self.user_turns = 0
        self.pending_confirmations: dict[tuple[str, str], int] = {}  # (tool, canonical args) -> turn asked
        self._notes: list[str] = []

    def request_messages(self, system_prompt: str) -> list[Message]:
        return [Message(role="system", content=system_prompt), *self.messages]

    def add(self, message: Message) -> None:
        self.messages.append(message)

    def add_note(self, note: str) -> None:
        self._notes.append(note)

    def _with_notes(self, text: str) -> str:
        return "".join(f"[Note: {n}]\n" for n in self._notes) + text

    def preview_messages(self, system_prompt: str, text: str) -> list[Message]:
        """The request add_user(text) would lead to, without changing anything: lets the first LLM call
        start on a speculative transcript. Trimming is left out, it only ever drops older context."""
        messages = self.request_messages(system_prompt)
        text = self._with_notes(text)
        if messages[-1].role == "user":
            messages[-1] = Message(role="user", content=f"{messages[-1].content}\n{text}")
        else:
            messages.append(Message(role="user", content=text))
        return messages

    def add_user(self, text: str) -> None:
        text = self._with_notes(text)
        self._notes.clear()
        self.user_turns += 1
        last = self.messages[-1] if self.messages else None
        if last and last.role == "user":  # previous turn produced no reply: keep roles alternating
            last.content = f"{last.content}\n{text}"
        else:
            self.messages.append(Message(role="user", content=text))
        self._trim()

    def _trim(self) -> None:
        if len(self.messages) <= MAX_MESSAGES:
            return
        cut = len(self.messages) - (MAX_MESSAGES - TRIM_BLOCK)
        # start history at a user message, so no tool result is left without its assistant call
        while cut < len(self.messages) and self.messages[cut].role != "user":
            cut += 1
        del self.messages[:cut]

    def mark_interrupted(self, heard: str) -> None:
        """Rewrite the current turn to what the user actually heard before barging in.
        Tool calls and their results stay (they happened); spoken text is replaced by `heard`."""
        start = next((i for i in range(len(self.messages) - 1, -1, -1) if self.messages[i].role == "user"), None)
        if start is None:
            return
        turn = []
        for m in self.messages[start + 1 :]:
            if m.role == "assistant" and m.tool_calls:
                turn.append(replace(m, content=None))
            elif m.role != "assistant":
                turn.append(m)
        if heard.strip():
            turn.append(Message(role="assistant", content=heard.strip()))
            self.add_note("The user interrupted your previous reply; your last message is only the part they heard.")
        else:
            self.add_note("The user interrupted before hearing any of your previous reply.")
        self.messages[start + 1 :] = turn
