"""RetryPolicy: exponential backoff with a circuit breaker."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable


class CircuitBreakerOpen(RuntimeError):
    """Raised when the circuit breaker is open (fast-fail)."""


class RetryPolicy:
    """Retries ``fn`` up to ``max_attempts`` times with backoff.

    After ``max_attempts`` consecutive failures the circuit breaker
    opens: subsequent ``execute`` calls fail fast with
    ``CircuitBreakerOpen`` until ``reset()`` is called.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        exponential: bool = True,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.exponential = exponential
        self._consecutive_failures = 0

    @property
    def is_open(self) -> bool:
        return self._consecutive_failures >= self.max_attempts

    def reset(self) -> None:
        self._consecutive_failures = 0

    async def execute(self, fn: Callable, *args, **kwargs) -> Any:
        if self.is_open:
            raise CircuitBreakerOpen("circuit breaker is open")

        attempt = 0
        last_error: Exception | None = None
        while attempt < self.max_attempts:
            try:
                result = fn(*args, **kwargs)
                if inspect.isawaitable(result):
                    result = await result
                self._consecutive_failures = 0
                return result
            except Exception as exc:  # noqa: BLE001 — retry any failure
                attempt += 1
                self._consecutive_failures = attempt
                last_error = exc
                if attempt >= self.max_attempts:
                    break
                delay = (
                    self.base_delay * (2 ** (attempt - 1))
                    if self.exponential
                    else self.base_delay
                )
                await asyncio.sleep(delay)

        raise CircuitBreakerOpen(
            f"failed after {self.max_attempts} attempts: {last_error}"
        ) from last_error
