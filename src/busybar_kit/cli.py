from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Iterable
from typing import TextIO

# Third-party loggers that log every request at INFO; quieted unless verbose.
CHATTY_LOGGERS = ("busylib", "httpx2", "httpcore2")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def create_base_parser(description: str = "BUSY Bar Application") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Device name from config/devices.toml (or BUSYBAR_DEVICE env var)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Explicit host/IP override (e.g. 192.168.1.42 or 10.0.4.20)",
    )
    parser.add_argument(
        "--token-env",
        type=str,
        default=None,
        help="Environment variable name holding the device API token",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform configuration and resolution without sending writes to device",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single update cycle and exit",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Polling interval in seconds when running continuously (default: 60)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    return parser


class SecretRedactionFilter(logging.Filter):
    """Replace known secret strings in log records with ``<redacted>``.

    Attach it to handlers, not loggers: logger filters do not see records propagated
    from child loggers such as ``busylib.client.base``. Covers the formatted message
    and exception text. Add secrets later with :meth:`add`.
    """

    def __init__(self, secrets: Iterable[str | None] = (), replacement: str = "<redacted>"):
        super().__init__()
        self.replacement = replacement
        self._secrets: set[str] = set()
        for secret in secrets:
            self.add(secret)

    def add(self, secret: str | None) -> None:
        if secret:
            self._secrets.add(secret)

    def _scrub(self, text: str) -> str:
        for secret in sorted(self._secrets, key=len, reverse=True):
            text = text.replace(secret, self.replacement)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        if not self._secrets:
            return True
        message = record.getMessage()
        scrubbed = self._scrub(message)
        if scrubbed != message:
            record.msg, record.args = scrubbed, None
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = self._scrub(record.exc_text)
        if record.stack_info:
            record.stack_info = self._scrub(record.stack_info)
        return True


class _Busylib409Filter(logging.Filter):
    """Drop busylib's ERROR line for each HTTP 409; busybar_kit.draw reports conflicts."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not (
            record.name.startswith("busylib")
            and isinstance(record.args, tuple)
            and record.args[:1] == (409,)
            and str(record.msg).startswith("API error")
        )


def setup_logging(
    verbose: bool = False,
    *,
    stream: TextIO | None = None,
    secrets: Iterable[str | None] = (),
) -> SecretRedactionFilter:
    """Configure root logging on ``stream`` (default ``sys.stderr``).

    stderr keeps stdout free for CLI output such as JSON. Unless ``verbose``,
    ``busylib``/``httpx2``/``httpcore2`` are limited to WARNING and busylib's per-409
    error line is dropped. Every record passes a :class:`SecretRedactionFilter` seeded
    with ``secrets``, which is returned so tokens resolved later can be added.
    """
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    redaction = SecretRedactionFilter(secrets)
    handler.addFilter(redaction)
    if not verbose:
        handler.addFilter(_Busylib409Filter())

    root = logging.getLogger()
    for old in [h for h in root.handlers if getattr(h, "_busybar_kit", False)]:
        root.removeHandler(old)
    handler._busybar_kit = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    for name in CHATTY_LOGGERS:
        logging.getLogger(name).setLevel(logging.NOTSET if verbose else logging.WARNING)
    return redaction
