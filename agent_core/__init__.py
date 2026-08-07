"""agent-core — reusable architectural layer for AI agents.

Versioned mutable state (continual harness), evidence tracking,
attention states, an evidence-first research pipeline and OKF v0.2
knowledge bundles. LLM-agnostic: every component accepts any async
callable as the language model.
"""

from .config import AgentCoreConfig

# state — continual harness H = (rho, G, K, M)
from .state.base import SQLiteVersionedState, VersionedState, VersionEntry
from .state.harness import HarnessSnapshot, HarnessState
from .state.memory import MemoryEntry, MemoryStore
from .state.skills import Skill, SkillRegistry, SkillResult
from .state.behavior import BehaviorAddend, BehaviorAddends
from .state.subagents import SubagentDefinition, SubagentRegistry
from .state.refine import RefineEngine, RefineResult

# runtime — execution loop
from .runtime.loop import AgentLoop, AgentResult
from .runtime.retry import CircuitBreakerOpen, RetryPolicy
from .runtime.compaction import ContextCompactor

# attention — explicit attention states
from .attention.states import AttentionState, AttentionTransition
from .attention.manager import AttentionManager

# research — evidence-first pipeline
from .research.pipeline import ResearchPipeline, ResearchResult
from .research.evidence import Evidence, Source
from .research.planner import ResearchPlanner

# format — OKF v0.2 knowledge bundles
from .format.bundle import KnowledgeBundle
from .format.concept import Concept
from .format.frontmatter import (
    parse_frontmatter,
    validate_frontmatter,
    write_frontmatter,
)
from .format.trust import TrustTier, credibility_score

# evidence — tracking + attestation
from .evidence.record import EvidenceRecord
from .evidence.chain import EvidenceChain
from .evidence.attestation import AttestedComputation, Receipt

__version__ = "0.1.0"

__all__ = [
    "AgentCoreConfig",
    # state
    "VersionedState",
    "SQLiteVersionedState",
    "VersionEntry",
    "HarnessState",
    "HarnessSnapshot",
    "MemoryStore",
    "MemoryEntry",
    "SkillRegistry",
    "Skill",
    "SkillResult",
    "BehaviorAddends",
    "BehaviorAddend",
    "SubagentRegistry",
    "SubagentDefinition",
    "RefineEngine",
    "RefineResult",
    # runtime
    "AgentLoop",
    "AgentResult",
    "RetryPolicy",
    "CircuitBreakerOpen",
    "ContextCompactor",
    # attention
    "AttentionState",
    "AttentionTransition",
    "AttentionManager",
    # research
    "ResearchPipeline",
    "ResearchResult",
    "ResearchPlanner",
    "Evidence",
    "Source",
    # format
    "KnowledgeBundle",
    "Concept",
    "parse_frontmatter",
    "write_frontmatter",
    "validate_frontmatter",
    "TrustTier",
    "credibility_score",
    # evidence
    "EvidenceRecord",
    "EvidenceChain",
    "AttestedComputation",
    "Receipt",
]
