"""KnowledgeBundle: a directory of OKF v0.2 concept files."""

from __future__ import annotations

from pathlib import Path

from .concept import Concept
from .frontmatter import validate_frontmatter


class KnowledgeBundle:
    """A knowledge bundle is a directory of ``*.md`` concept files.

    Each file carries OKF v0.2 YAML frontmatter; the concept id is the
    file path relative to the bundle root, without the ``.md`` suffix.
    """

    def __init__(self, path: str):
        self.path = Path(path)
        self._concepts: dict[str, Concept] = {}

    def load(self) -> None:
        """Scan the bundle directory and parse every ``*.md`` file."""
        self._concepts = {}
        if not self.path.exists():
            return
        for p in sorted(self.path.rglob("*.md")):
            concept_id = p.relative_to(self.path).as_posix()[:-3]
            self._concepts[concept_id] = Concept.from_markdown(
                p.read_text(encoding="utf-8"), concept_id
            )

    def get(self, concept_id: str) -> Concept | None:
        return self._concepts.get(concept_id)

    def list(self) -> list[str]:
        return sorted(self._concepts)

    def add(self, concept: Concept) -> None:
        """Add a concept to the in-memory bundle (persist with ``write``)."""
        self._concepts[concept.id] = concept

    def remove(self, concept_id: str) -> bool:
        if concept_id in self._concepts:
            del self._concepts[concept_id]
            return True
        return False

    def validate(self) -> list[str]:
        """Check OKF v0.2 compliance of every concept in the bundle."""
        errors: list[str] = []
        for cid, concept in self._concepts.items():
            if cid != concept.id:
                errors.append(f"{cid}: id does not match concept.id ({concept.id})")
            errors.extend(
                f"{cid}: {e}" for e in validate_frontmatter({"type": concept.type})
            )
            if not concept.body.strip():
                errors.append(f"{cid}: empty body")
        return errors

    def write(self) -> None:
        """Write all concepts to disk as ``<id>.md`` files."""
        for concept in self._concepts.values():
            target = self.path / f"{concept.id}.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(concept.to_markdown(), encoding="utf-8")
