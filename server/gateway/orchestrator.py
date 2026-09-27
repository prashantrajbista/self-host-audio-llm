from server.adapters.llm.base import LLMAdapter, Message
from server.adapters.stt.base import STTAdapter
from server.adapters.tts.base import TTSAdapter


class Orchestrator:
    def __init__(self, stt: STTAdapter, llm: LLMAdapter, tts: TTSAdapter):
        self._stt = stt
        self._llm = llm
        self._tts = tts

    async def run_turn(self, audio: bytes) -> tuple[str, str, bytes]:
        """Non-streaming: full utterance in, full reply audio out. Returns (transcript, reply_text, audio)."""
        transcript = ""
        async for event in self._stt.transcribe_stream(audio):
            if event.is_final:
                transcript = event.text

        reply_text = ""
        async for token in self._llm.generate_stream([Message(role="user", content=transcript)]):
            reply_text += token

        audio_out = b""
        async for chunk in self._tts.synthesize_stream(reply_text):
            audio_out += chunk

        return transcript, reply_text, audio_out
