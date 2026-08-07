"""AttestedComputation: run + deterministic verification + receipt."""

from __future__ import annotations

import asyncio
import inspect
import json
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable


@dataclass
class Receipt:
    """Proof that a computation ran and passed its attester."""

    job_id: str
    executed_at: datetime
    inputs: dict
    outputs: dict
    attester_verdict: bool  # passed/failed


class AttestedComputation:
    """A computation whose result is checked by a deterministic attester.

    ``executor`` and ``attester`` are either:
      * an async/sync callable (preferred for embedding), or
      * a path to an executable script that reads a JSON payload from
        argv[1] and prints a JSON result to stdout.

    No external services are involved.
    """

    def __init__(self, concept_id: str, executor: Any, attester: Any, parameters: dict):
        self.concept_id = concept_id  # OKF concept path
        self.executor = executor  # path to run instructions (or callable)
        self.attester = attester  # path to deterministic checker (or callable)
        self.parameters = dict(parameters)

    async def run(self, inputs: dict) -> Receipt:
        job_id = uuid.uuid4().hex[:12]
        merged = {**self.parameters, **inputs}
        outputs = await self._invoke(self.executor, merged)
        verdict = await self._invoke(self.attester, outputs)
        verdict = self._coerce_verdict(verdict)
        return Receipt(
            job_id=job_id,
            executed_at=datetime.now(),
            inputs=merged,
            outputs=outputs,
            attester_verdict=verdict,
        )

    async def _invoke(self, target: Any, payload: dict) -> Any:
        if callable(target):
            result = target(payload)
            if inspect.isawaitable(result):
                result = await result
            return result
        # path-based execution: JSON payload via argv[1], JSON result on stdout
        path = str(target)
        cmd = [sys.executable, path, json.dumps(payload)] if path.endswith(".py") else [path, json.dumps(payload)]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"attested computation failed (exit {proc.returncode}): {err.decode()[:500]}"
            )
        return json.loads(out.decode())

    @staticmethod
    def _coerce_verdict(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, dict):
            v = value.get("verdict", value.get("passed", False))
            return AttestedComputation._coerce_verdict(v)
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "pass", "passed", "ok"}
        return bool(value)
