"""AgentLoop: the main plan -> act -> observe -> reflect loop.

LLM contract: an async callable ``llm(prompt: dict) -> dict`` where the
prompt carries ``{"type": "agent_step", "task": ..., "state": ...}`` and
the answer carries ``{"action": str, "done": bool, "answer": str}``.
Everything the agent does lands in an EvidenceChain; every step moves
the AttentionManager.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from ..attention.manager import AttentionManager
from ..attention.states import AttentionState
from ..evidence.chain import EvidenceChain
from ..evidence.record import EvidenceRecord
from ..state.harness import HarnessState

_BASE_PROMPT = "You are an agent. Follow the task, keep evidence of every action."


@dataclass
class AgentResult:
    task: str
    answer: str
    iterations: int
    evidence_chain: list[EvidenceRecord]
    attention_log: list[AttentionTransition]


class AgentLoop:
    """plan -> act -> observe -> reflect."""

    def __init__(self, harness: HarnessState, llm: Callable, max_iterations: int = 10):
        self.harness = harness
        self.llm = llm
        self.max_iterations = max_iterations
        self.chain = EvidenceChain()
        self.attention = AttentionManager()

    async def run(self, task: str) -> AgentResult:
        await self.harness.skills.load_index()
        state: dict[str, Any] = {"task": task, "iterations": 0, "history": []}
        state["system_prompt"] = await self.harness.prompts.compose(_BASE_PROMPT)
        state["memory"] = [e.key for e in await self.harness.memory.by_confidence()]

        answer = ""
        iterations = 0
        for i in range(self.max_iterations):
            iterations = i + 1
            step_result = await self.step(task, state)
            if step_result["done"]:
                answer = step_result.get("answer") or answer
                break
            state["history"].append(step_result)
        else:
            if state["history"]:
                answer = state["history"][-1].get("answer", "")
            if not answer:
                answer = "max iterations reached without a final answer"

        return AgentResult(
            task=task,
            answer=answer,
            iterations=iterations,
            evidence_chain=self.chain.all(),
            attention_log=self.attention.history(),
        )

    async def step(self, task: str, state: dict) -> dict:
        """One iteration: LLM generates an action -> execute -> observe."""
        attention = (
            AttentionState.FOCUS
            if self.attention.should_focus(task)
            else AttentionState.DIFFUSE
        )
        self.attention.transition(
            attention, f"step {state.get('iterations', 0) + 1} for task: {task[:40]}"
        )

        out = await self.llm({"type": "agent_step", "task": task, "state": state})
        action = str(out.get("action", "noop"))
        done = bool(out.get("done", False))
        answer = out.get("answer", "")
        error = out.get("error")

        record = EvidenceRecord(
            id=uuid.uuid4().hex[:12],
            action=action,
            actor="agent:loop",
            timestamp=datetime.now(),
            inputs={"task": task, "state": state},
            outputs={"answer": answer},
            success=error is None,
            error=error,
        )
        self.chain.add(record)

        state["iterations"] = state.get("iterations", 0) + 1
        state["last_action"] = action
        observation = str(out.get("observation", f"executed: {action}"))
        return {
            "action": action,
            "done": done,
            "answer": answer,
            "observation": observation,
            "record_id": record.id,
        }
