#!/usr/bin/env python3
"""Hard-stop gates and stall detection.

A hard-stop gate blocks a high-cost/high-volume run until the operator
confirms in the terminal. Stall detection aborts a run when no progress
(heartbeat) is observed inside the configured timeout.
"""

from __future__ import annotations

import threading
import time


class GateAborted(Exception):
    """Raised when the operator declines or the terminal is closed."""


def hard_stop_gate(reason: str, confirm_text: str = "YES") -> None:
    """Block until the operator types the confirmation word.

    Raises GateAborted when input is unavailable (EOF) or the operator
    types anything else.
    """
    print(f"\n[GATE] {reason}")
    try:
        answer = input(f"Type '{confirm_text}' to continue (anything else aborts): ")
    except EOFError as exc:
        raise GateAborted("no terminal available for gate confirmation") from exc
    if answer.strip() != confirm_text:
        raise GateAborted("gate declined by operator")


class StallError(TimeoutError):
    """Raised by StallDetector when no progress was observed in time."""


class StallDetector:
    """Aborts if no heartbeat arrives within the stall timeout.

    The watchdog runs in a daemon thread and sets a stalled flag; the
    main thread must call `check()` (e.g. from the pipeline loop) so the
    StallError surfaces on the executing thread.
    """

    def __init__(self, timeout_seconds: float) -> None:
        self.timeout = timeout_seconds
        self._last = time.monotonic()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._stalled = threading.Event()

    def beat(self) -> None:
        with self._lock:
            self._last = time.monotonic()

    def check(self) -> None:
        if self._stalled.is_set():
            raise StallError(f"stall detected: no progress for {self.timeout:.0f}s")

    def _watch(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                idle = time.monotonic() - self._last
            if idle > self.timeout:
                self._stalled.set()
                return
            time.sleep(min(1.0, self.timeout))

    def __enter__(self) -> "StallDetector":
        self._thread = threading.Thread(target=self._watch, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._stop.set()
