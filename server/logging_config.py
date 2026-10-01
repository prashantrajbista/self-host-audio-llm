import json
import logging
import sys
from datetime import UTC, datetime

from server import context

_NOISY_LOGGERS = ("httpx", "httpcore", "huggingface_hub", "urllib3", "websockets")
_STANDARD = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "taskName"}


class _Context(logging.Filter):
    """Stamp every record with the current interview and user (server/context.py)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.session_id = context.session_id.get()
        record.user_id = context.user_id.get()
        return True


class JSONFormatter(logging.Formatter):
    """One JSON object per line, for a log shipper to index: fixed fields, the context ids, and any `extra=`."""

    def format(self, record: logging.LogRecord) -> str:
        out = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        out |= {k: v for k, v in record.__dict__.items() if k not in _STANDARD and v is not None}
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        return json.dumps(out, default=str)


def setup_logging(level: str = "INFO", fmt: str = "text") -> None:
    """fmt: "text" for reading in a terminal, "json" in production (one object per line, for searching or a log shipper)."""
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_Context())
    if fmt == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s", "%H:%M:%S"))
    logging.basicConfig(level=level, handlers=[handler], force=True)
    # keep DEBUG focused on our own code — these libraries are extremely chatty at DEBUG
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
