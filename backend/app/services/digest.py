"""Digest generation + delivery (PRD §6.7)."""
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ActionItem, Decision, Person, Digest
from .notify import send_notification


def _week_start(dt: datetime | None = None) -> str:
    d = (dt or datetime.utcnow()).date()
    monday = d - timedelta(days=d.weekday())
    return monday.isoformat()


async def generate_digest_for_person(person_id: str, db: AsyncSession) -> dict:
    """Generate weekly digest payload for a person."""
    today = datetime.utcnow().date().isoformat()
    week_end = (datetime.utcnow().date() + timedelta(days=7)).isoformat()

    items = (await db.execute(select(ActionItem).where(
        ActionItem.owner_id == person_id,
        ActionItem.status.in_(["posted", "approved"]),
    ))).scalars().all()

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    decs = (await db.execute(select(Decision).where(
        Decision.status == "active",
        Decision.decided_at >= seven_days_ago,
    ))).scalars().all()

    due_this_week = [
        {"id": i.id, "title": i.title, "due_date": i.due_date}
        for i in items
        if i.due_date and today <= i.due_date <= week_end
    ]
    overdue = [
        {"id": i.id, "title": i.title, "due_date": i.due_date}
        for i in items
        if i.due_date and i.due_date < today
    ]
    open_items = [
        {"id": i.id, "title": i.title, "due_date": i.due_date, "status": i.status}
        for i in items
        if not i.completed_at
    ]

    return {
        "person_id": person_id,
        "week_start": _week_start(),
        "due_this_week": due_this_week,
        "overdue": overdue,
        "open_items": open_items,
        "decisions_that_affect_you": [
            {"id": d.id, "statement": d.statement, "topic": d.topic} for d in decs
        ],
    }


async def send_weekly_digests(db: AsyncSession) -> dict:
    """Generate and deliver a weekly digest for every person."""
    people = (await db.execute(select(Person))).scalars().all()
    week = _week_start()
    sent = 0
    skipped = 0
    for person in people:
        existing = await db.execute(
            select(Digest).where(Digest.person_id == person.id, Digest.week_start == week)
        )
        if existing.scalars().first():
            skipped += 1
            continue

        payload = await generate_digest_for_person(person.id, db)
        # Skip empty digests for people with nothing assigned
        if not (payload["due_this_week"] or payload["overdue"] or payload["open_items"]):
            skipped += 1
            continue

        lines = [
            f"Weekly digest for {person.name}",
            f"Due this week: {len(payload['due_this_week'])}",
            f"Overdue: {len(payload['overdue'])}",
            f"Open items: {len(payload['open_items'])}",
            f"Recent decisions: {len(payload['decisions_that_affect_you'])}",
        ]
        for item in payload["overdue"][:5]:
            lines.append(f"  OVERDUE: {item['title']} ({item['due_date']})")
        for item in payload["due_this_week"][:5]:
            lines.append(f"  Due: {item['title']} ({item['due_date']})")

        await send_notification(
            subject=f"Weekly digest — {person.name}",
            body="\n".join(lines),
            recipient=person.email,
            channel="console",
            payload=payload,
        )
        db.add(Digest(
            person_id=person.id,
            week_start=week,
            payload=payload,
            sent_at=datetime.utcnow(),
        ))
        sent += 1

    await db.commit()
    return {"week_start": week, "sent": sent, "skipped": skipped, "people": len(people)}
