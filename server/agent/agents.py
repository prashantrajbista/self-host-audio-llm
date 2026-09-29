import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime
from functools import cached_property
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from server.agent.tools import Tool, tool

# Everything the model writes is spoken aloud by TTS, so ask for speakable text up front rather than
# relying only on the session's markdown stripping (which remains as a safety net).
VOICE_PROMPT = (
    "You are a friendly voice assistant in a live spoken conversation. Everything you write is read aloud "
    "by a text-to-speech engine, so write only what should be spoken.\n"
    "- Keep answers short: a sentence or two unless the user asks for more detail.\n"
    "- Talk like a person: plain conversational sentences, contractions, no filler.\n"
    "- Never use markdown, bullet points, numbered lists, headings, tables, code blocks, emojis, or URLs. "
    "If you need to list things, say them in a sentence, like \"first..., then..., and finally...\".\n"
    "- Write numbers, dates, times, units, and symbols the way they're said: \"twenty-five degrees\", "
    "\"three thirty pm\", \"about five percent\", \"forty dollars\".\n"
    "- Spell out abbreviations that aren't normally said as letters, and avoid parentheses.\n"
    "- The user's words come from speech-to-text and may contain mishearings. If a message seems oddly worded or "
    "out of context, ask what they meant instead of guessing.\n"
    "- If the request is unclear or you didn't catch it, briefly ask the user to repeat or clarify."
)
TOOLS_PROMPT = (
    "- You can use tools. Before calling one, say a very short phrase first, like \"let me check\", so the "
    "user isn't left in silence. Never read tool output verbatim; summarize it in speech.\n"
    "- Some actions need the user's confirmation. When a tool tells you so, read the details back and ask; "
    "only call it again if the user clearly agrees."
)


@dataclass(frozen=True)
class AgentDef:
    """What an agent is: prompt, tools, LLM params, voice. A new domain = a new AgentDef, no harness changes."""

    name: str
    instructions: str = ""
    tools: tuple[Tool, ...] = ()
    llm_params: dict = field(default_factory=dict)  # extra request params, e.g. temperature, max_tokens
    voice: str | None = None
    max_steps: int = 4  # LLM calls per user turn (tool rounds + final answer)

    # shared base first, agent-specific text last: keeps the cached prompt prefix identical across agents
    @cached_property
    def system_prompt(self) -> str:
        parts = [VOICE_PROMPT, TOOLS_PROMPT if self.tools else "", self.instructions]
        return "\n".join(p for p in parts if p)

    @cached_property
    def tool_schemas(self) -> list[dict] | None:
        return [t.schema for t in self.tools] or None


@tool(timeout=2.0)
async def get_time(timezone: str = "UTC") -> str:
    """Get the current date and time.

    Args:
        timezone: IANA timezone name, like America/New_York or Asia/Kathmandu
    """
    try:
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return f"Error: unknown timezone {timezone}."
    return datetime.now(tz).strftime("%A %d %B %Y, %I:%M %p %Z")


@tool(timeout=5.0, filler="Let me look that up.")
async def lookup_weather(city: str) -> str:
    """Look up the current weather for a city. Demo tool: returns mock data after a delay.

    Args:
        city: city name
    """
    await asyncio.sleep(1.5)
    return f"Mock data: {city} is twenty-two degrees Celsius and partly cloudy."


@tool(side_effect=True, timeout=5.0)
async def book_appointment(name: str, day: str, time: str) -> str:
    """Book an appointment. Demo tool: pretends to book and returns a reference number.

    Args:
        name: the person's name
        day: the day, like Monday or March third
        time: the time, like three pm
    """
    return f"Booked {name} on {day} at {time}. Reference number {random.randint(1000, 9999)}."


AGENTS: dict[str, AgentDef] = {
    "assistant": AgentDef(name="assistant", tools=(get_time,)),
    "demo_tools": AgentDef(
        name="demo_tools",
        instructions="You can tell the time, check the weather, and book appointments.",
        tools=(get_time, lookup_weather, book_appointment),
    ),
}


def get_agent(name: str | None, default: str) -> AgentDef:
    return AGENTS.get(name or "") or AGENTS.get(default) or AGENTS["assistant"]
