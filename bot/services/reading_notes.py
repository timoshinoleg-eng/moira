"""Private per-reading notes. Note text never reaches analytics, logs, or LLM prompts."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Reading, ReadingNote

MAX_NOTE_LENGTH = 1000


class NoteOwnershipError(ValueError):
    """Raised when a user touches a reading that is missing or belongs to someone else."""


async def _owned_reading(session: AsyncSession, *, user_id: int, reading_id: int) -> Reading:
    reading = await session.get(Reading, reading_id)
    if reading is None or reading.user_id != user_id:
        raise NoteOwnershipError("foreign reading")
    return reading


async def save_reading_note(session: AsyncSession, *, user_id: int, reading_id: int, text: str) -> ReadingNote:
    """Upsert a note. Truncates to MAX_NOTE_LENGTH; empty text is rejected."""
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("empty note")
    await _owned_reading(session, user_id=user_id, reading_id=reading_id)
    note = await session.scalar(select(ReadingNote).where(ReadingNote.reading_id == reading_id))
    if note is None:
        note = ReadingNote(user_id=user_id, reading_id=reading_id, text=cleaned[:MAX_NOTE_LENGTH])
        session.add(note)
    else:
        if note.user_id != user_id:
            raise NoteOwnershipError("foreign reading")
        note.text = cleaned[:MAX_NOTE_LENGTH]
    return note


async def delete_reading_note(session: AsyncSession, *, user_id: int, reading_id: int) -> bool:
    """Delete a note. Returns True when a row was removed."""
    await _owned_reading(session, user_id=user_id, reading_id=reading_id)
    note = await session.scalar(select(ReadingNote).where(ReadingNote.reading_id == reading_id))
    if note is None:
        return False
    if note.user_id != user_id:
        raise NoteOwnershipError("foreign reading")
    await session.delete(note)
    return True


async def get_reading_note(session: AsyncSession, *, user_id: int, reading_id: int) -> ReadingNote | None:
    """Return the user's note for a reading, or None. Ownership-checked."""
    await _owned_reading(session, user_id=user_id, reading_id=reading_id)
    note = await session.scalar(select(ReadingNote).where(ReadingNote.reading_id == reading_id))
    if note is not None and note.user_id != user_id:
        raise NoteOwnershipError("foreign reading")
    return note
