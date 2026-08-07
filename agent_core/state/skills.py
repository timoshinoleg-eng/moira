"""SkillRegistry: progressive loading of SKILL.md files (DeerFlow).

Skills live on disk as ``<name>.md`` files with YAML frontmatter
(``name``, ``description``, ``trigger``, ``version``). Only the index
(name -> path) is loaded eagerly; bodies are loaded on demand and
cached in memory after the first access.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..format.frontmatter import parse_frontmatter, write_frontmatter
from .base import VersionedState, VersionEntry

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass
class Skill:
    name: str
    description: str
    trigger: str  # when to apply
    body: str  # markdown content
    path: str  # path to the file
    version: str  # from frontmatter
    loaded_at: Optional[datetime] = None  # None = not loaded (lazy)


@dataclass
class SkillResult:
    name: str
    output: str
    context: dict
    ok: bool = True
    error: Optional[str] = None


class SkillRegistry(VersionedState):
    """File-backed skill store with progressive (lazy) loading."""

    def __init__(self, skills_dir: str):
        self.skills_dir = Path(skills_dir)
        self._index: dict[str, Path] = {}
        self._cache: dict[str, Skill] = {}
        self._loaded = False
        self._put_counter = 0  # per-write version counter for the ABC API

    # ------------------------------------------------------------ core API

    def _file_for(self, name: str) -> Path:
        return self.skills_dir / f"{name}.md"

    async def load_index(self) -> None:
        """Load only the index (name -> path); do not load bodies."""
        self._index = {}
        if self.skills_dir.exists():
            for p in sorted(self.skills_dir.glob("*.md")):
                meta, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
                name = meta.get("name") or p.stem
                if _NAME_RE.match(str(name)):
                    self._index[str(name)] = p
        self._loaded = True

    async def get(self, name: str, version: Optional[int] = None) -> Optional[Skill]:
        """Lazy-load a skill body; cache it after the first access."""
        if not self._loaded:
            await self.load_index()
        if name in self._cache:
            return self._cache[name]
        path = self._index.get(name)
        if path is None:
            return None
        content = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)
        skill = Skill(
            name=name,
            description=str(meta.get("description", "")),
            trigger=str(meta.get("trigger", "")),
            body=body,
            path=str(path),
            version=str(meta.get("version", "0.0.1")),
            loaded_at=datetime.now(),
        )
        self._cache[name] = skill
        return skill

    async def list(self) -> list[str]:
        """Names from the index only (no bodies loaded)."""
        if not self._loaded:
            await self.load_index()
        return sorted(self._index)

    async def validate(self, skill: Skill) -> list[str]:
        errors: list[str] = []
        if not skill.name:
            errors.append("name is empty")
        elif not _NAME_RE.match(skill.name):
            errors.append("name must be lowercase with hyphens (a-z0-9-)")
        if not skill.description:
            errors.append("description is empty")
        if not skill.trigger:
            errors.append("trigger is empty")
        if len(skill.body) <= 100:
            errors.append(f"body too short ({len(skill.body)} chars, need > 100)")
        return errors

    async def invoke(self, name: str, context: dict) -> SkillResult:
        """Load the skill and apply it to ``context``.

        ``{placeholder}`` tokens in the body are substituted with
        context values; the result carries the rendered body.
        """
        skill = await self.get(name)
        if skill is None:
            return SkillResult(name=name, output="", context=context,
                               ok=False, error=f"skill not found: {name}")
        errors = await self.validate(skill)
        if errors:
            return SkillResult(name=name, output="", context=context,
                               ok=False, error="; ".join(errors))
        output = skill.body
        for key, value in context.items():
            output = output.replace("{" + key + "}", str(value))
        return SkillResult(name=name, output=output, context=context, ok=True)

    # ------------------------------------------------------- VersionedState ABC
    # Skills are declarative files; the ABC methods are file-backed:
    #   put      — write a SKILL.md (backing up the previous version)
    #   rollback — restore a file from its backup
    #   history  — list backups (versions) of a skill

    async def put(
        self, key: str, value: Any, *, actor: str = "agent", scope: str = "session"
    ) -> int:
        self._put_counter += 1
        version = self._put_counter
        skill = value if isinstance(value, Skill) else None
        if skill is None:
            skill = Skill(name=key, description="", trigger="",
                          body=str(value), path="", version="0.0.1")
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        target = self._file_for(key)
        if target.exists():  # back up the version being replaced
            backup_dir = self.skills_dir / ".backups"
            backup_dir.mkdir(exist_ok=True)
            (backup_dir / f"{key}.{version - 1}.bak").write_text(
                target.read_text(encoding="utf-8"), encoding="utf-8"
            )
        meta = {
            "name": skill.name,
            "description": skill.description,
            "trigger": skill.trigger,
            "version": skill.version,
        }
        target.write_text(write_frontmatter(meta, skill.body), encoding="utf-8")
        self._index[key] = target
        self._cache.pop(key, None)
        return version

    async def rollback(self, version: int) -> bool:
        """Restore the file written by put-call ``version`` from its backup."""
        backup_dir = self.skills_dir / ".backups"
        if not backup_dir.exists():
            return False
        candidates = sorted(backup_dir.glob(f"*.{version}.bak"))
        if not candidates:
            return False
        path = candidates[0]
        key = path.name[: -(len(str(version)) + 5)]  # strip ".<version>.bak"
        target = self._file_for(key)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        path.unlink()
        self._index[key] = target
        self._cache.pop(key, None)
        return True

    async def history(self, key: str) -> list[VersionEntry]:
        backup_dir = self.skills_dir / ".backups"
        entries: list[VersionEntry] = []
        if backup_dir.exists():
            for p in sorted(backup_dir.glob(f"{key}.*.bak")):
                version = int(p.name.rsplit(".", 2)[1])
                entries.append(
                    VersionEntry(
                        version=version, key=key, value=p.read_text(encoding="utf-8"),
                        timestamp=datetime.fromtimestamp(p.stat().st_mtime),
                        actor="agent", scope="session",
                    )
                )
        return entries

    # ------------------------------------------------------------------ helpers

    def mirror_index(self) -> dict[str, Path]:
        """Sync mirror of the index (for HarnessState.snapshot)."""
        if not self._loaded:
            return dict(self._index)
        return dict(self._index)
