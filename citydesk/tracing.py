"""A tiny trace the UI can show next to a run.

Middleware and tools call ``emit``. The counter opens a ``trace_scope``
around ``invoke`` and reads the events back.
"""

from __future__ import annotations

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager

_current: contextvars.ContextVar[list[dict[str, str]] | None] = contextvars.ContextVar(
    "citydesk_trace",
    default=None,
)


def emit(hook: str, detail: str) -> None:
    log = _current.get()
    if log is None:
        return
    log.append({"hook": hook, "detail": detail})


@contextmanager
def trace_scope() -> Iterator[list[dict[str, str]]]:
    events: list[dict[str, str]] = []
    token = _current.set(events)
    try:
        yield events
    finally:
        _current.reset(token)
