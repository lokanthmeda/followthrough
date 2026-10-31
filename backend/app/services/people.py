"""Resolve speaker / owner names to Person rows (create if missing)."""
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Person


async def resolve_or_create_person(db: AsyncSession, name: str | None) -> Person | None:
    """Find a person by name / alias (case-insensitive) or create one."""
    if not name or not str(name).strip():
        return None
    clean = str(name).strip()
    # Exact name match (case-insensitive)
    result = await db.execute(
        select(Person).where(func.lower(Person.name) == clean.lower())
    )
    person = result.scalars().first()
    if person:
        return person

    # Alias match
    result = await db.execute(select(Person))
    for p in result.scalars().all():
        aliases = p.aliases or []
        if any(str(a).lower() == clean.lower() for a in aliases):
            return p

    person_id = str(uuid.uuid4())
    person = Person(
        id=person_id,
        name=clean,
        email=f"{clean.lower().replace(' ', '.')}@example.com",
        aliases=[],
    )
    db.add(person)
    # Flush, never commit: callers (pipeline, review) own the outer transaction.
    # An inner commit() on SQLite breaks the enclosing session and causes
    # "database is locked" when the outer transaction continues.
    await db.flush()
    return person


async def person_name_map(db: AsyncSession, person_ids: list[str | None]) -> dict[str, str]:
    ids = [i for i in person_ids if i]
    if not ids:
        return {}
    result = await db.execute(select(Person).where(Person.id.in_(ids)))
    return {p.id: p.name for p in result.scalars().all()}
