"""Deadline reminder scheduling and delivery (PRD §6.6)."""
from datetime import datetime, timedelta, time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ActionItem, Reminder, Person
from .notify import send_notification


def _parse_due(due_date: str) -> datetime | None:
    try:
        d = datetime.fromisoformat(due_date)
        if d.hour == 0 and d.minute == 0:
            return datetime.combine(d.date(), time(9, 0))
        return d
    except Exception:
        try:
            return datetime.strptime(due_date, "%Y-%m-%d").replace(hour=9, minute=0)
        except Exception:
            return None


async def schedule_reminders_for_item(db: AsyncSession, item: ActionItem) -> list[Reminder]:
    """Create T-24h, due-day, and overdue reminders for a posted action item."""
    if not item.due_date:
        return []
    due = _parse_due(item.due_date)
    if not due:
        return []

    now = datetime.utcnow()
    planned = [
        ("t24h", due - timedelta(hours=24)),
        ("due_day", due),
        ("overdue", due + timedelta(days=1)),
    ]
    created: list[Reminder] = []
    for kind, send_at in planned:
        # If the planned time already passed, send ASAP (still covers "before deadline")
        effective = send_at if send_at >= now else now
        # Skip overdue reminders that are far in the future relative to due+1d planning only
        if kind == "overdue" and due + timedelta(days=1) > now + timedelta(days=365):
            continue
        existing = await db.execute(
            select(Reminder).where(
                Reminder.action_item_id == item.id,
                Reminder.kind == kind,
            )
        )
        if existing.scalars().first():
            continue
        rem = Reminder(
            action_item_id=item.id,
            kind=kind,
            send_at=effective,
            channel="console",
            status="scheduled",
        )
        db.add(rem)
        created.append(rem)
    await db.flush()
    return created


async def process_due_reminders(db: AsyncSession) -> dict:
    """Send all scheduled reminders whose send_at has passed."""
    now = datetime.utcnow()
    result = await db.execute(
        select(Reminder).where(
            Reminder.status == "scheduled",
            Reminder.send_at <= now,
        )
    )
    due = result.scalars().all()
    sent = 0
    failed = 0
    for rem in due:
        item = await db.get(ActionItem, rem.action_item_id)
        if not item or item.status not in ("posted", "approved"):
            rem.status = "skipped"
            continue
        owner = await db.get(Person, item.owner_id) if item.owner_id else None
        recipient = owner.email if owner else None
        label = {
            "t24h": "Due in 24 hours",
            "due_day": "Due today",
            "overdue": "OVERDUE",
        }.get(rem.kind or "", rem.kind or "reminder")
        body = (
            f"Action item: {item.title}\n"
            f"Due: {item.due_date}\n"
            f"Owner: {owner.name if owner else 'unassigned'}\n"
            f"Kind: {label}"
        )
        try:
            await send_notification(
                subject=f"Reminder: {label} — {item.title}",
                body=body,
                recipient=recipient,
                channel=rem.channel or "console",
                payload={"reminder_id": rem.id, "action_item_id": item.id, "kind": rem.kind},
            )
            rem.sent_at = now
            rem.status = "sent"
            sent += 1
        except Exception:
            rem.status = "failed"
            failed += 1
    await db.commit()
    return {"checked": len(due), "sent": sent, "failed": failed}
