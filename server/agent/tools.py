import asyncio
import inspect
import json
import logging
import re
import types
import typing
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MAX_RESULT_CHARS = 2000  # a huge tool result would bloat the prompt and every later request's prefill

_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean", dict: "object"}


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict  # JSON schema
    fn: Callable[..., Awaitable[typing.Any]]
    timeout: float
    side_effect: bool  # changes the world: needs user confirmation, never cancelled mid-flight
    filler: str | None  # spoken if the tool is slow

    @property
    def schema(self) -> dict:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}


def _type_schema(tp) -> dict:
    origin, args = typing.get_origin(tp), typing.get_args(tp)
    if origin is typing.Literal:
        return {"type": _JSON_TYPES.get(type(args[0]), "string"), "enum": list(args)}
    if origin in (typing.Union, types.UnionType):  # Optional[X] / X | None
        non_none = [a for a in args if a is not type(None)]
        return _type_schema(non_none[0]) if len(non_none) == 1 else {}
    if origin is list or tp is list:
        return {"type": "array", "items": _type_schema(args[0]) if args else {}}
    return {"type": _JSON_TYPES.get(origin or tp, "string")}


def _parse_docstring(doc: str) -> tuple[str, dict[str, str]]:
    """Description = text before 'Args:'; param docs = 'name: text' lines under it."""
    head, _, args_block = doc.partition("Args:")
    params = dict(re.findall(r"^\s*(\w+)\s*(?:\([^)]*\))?:\s*(.+)$", args_block, re.MULTILINE))
    return " ".join(head.split()), params


def tool(fn=None, *, timeout: float = 5.0, side_effect: bool = False, filler: str | None = None):
    """Turn an async function into a Tool; schema comes from its type hints and docstring."""

    def wrap(f) -> Tool:
        # one event loop serves every call in the process: a blocking tool would stall all of them
        if not inspect.iscoroutinefunction(f):
            raise TypeError(f"tool {f.__name__} must be async; wrap blocking code in asyncio.to_thread")
        description, param_docs = _parse_docstring(inspect.getdoc(f) or "")
        hints = typing.get_type_hints(f)
        props, required = {}, []
        for name, p in inspect.signature(f).parameters.items():
            props[name] = _type_schema(hints.get(name, str))
            if name in param_docs:
                props[name]["description"] = param_docs[name]
            if p.default is inspect.Parameter.empty:
                required.append(name)
        params = {"type": "object", "properties": props, "required": required}
        return Tool(f.__name__, description or f.__name__, params, f, timeout, side_effect, filler)

    return wrap(fn) if fn else wrap


async def execute(t: Tool, arguments: str) -> str:
    """Run a tool call; every failure becomes a string for the model, never an exception for the turn."""
    try:
        args = json.loads(arguments or "{}")
        if not isinstance(args, dict):
            raise ValueError("arguments must be a JSON object")
    except ValueError as e:
        return f"Error: invalid arguments JSON ({e}). Call the tool again with valid arguments."
    try:
        async with asyncio.timeout(t.timeout):
            result = await t.fn(**args)
    except TimeoutError:
        return f"Error: {t.name} timed out after {t.timeout:.0f} seconds."
    except TypeError as e:  # wrong/missing argument names
        return f"Error: bad arguments for {t.name}: {e}"
    except Exception as e:
        logger.exception("tool %s failed", t.name)
        return f"Error: {t.name} failed: {e}"
    text = result if isinstance(result, str) else json.dumps(result, default=str)
    return text if len(text) <= MAX_RESULT_CHARS else text[:MAX_RESULT_CHARS] + " ...[truncated]"
