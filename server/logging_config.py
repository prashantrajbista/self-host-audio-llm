import logging
import sys


_NOISY_LOGGERS = ("httpx", "httpcore", "huggingface_hub", "urllib3", "websockets")


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    # keep DEBUG focused on our own code — these libraries are extremely chatty at DEBUG
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
