"""Manual job triggers for demo + ops (reminders / digests)."""
from fastapi import APIRouter
from sqlalchemy import select

from ..db import get_db_cm as get_db
from ..models import Reminder, Digest, Person
from ..services.reminders import process_due_reminders
from ..services.digest import send_weekly_digests

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/run-reminders")
async def trigger_reminders():
    async with get_db() as db:
        return await process_due_reminders(db)


@router.post("/run-digests")
async def trigger_digests():
    async with get_db() as db:
        return await send_weekly_digests(db)


@router.get("/reminders")
async def list_reminders():
    async with get_db() as db:
        rows = (await db.execute(select(Reminder).order_by(Reminder.send_at.desc()))).scalars().all()
        return [
            {
                "id": r.id,
                "action_item_id": r.action_item_id,
                "kind": r.kind,
                "send_at": r.send_at.isoformat() if r.send_at else None,
                "sent_at": r.sent_at.isoformat() if r.sent_at else None,
                "status": r.status,
                "channel": r.channel,
            }
            for r in rows
        ]


@router.get("/digests")
async def list_digests():
    async with get_db() as db:
        rows = (await db.execute(select(Digest).order_by(Digest.sent_at.desc()))).scalars().all()
        people = {
            p.id: p.name
            for p in (await db.execute(select(Person))).scalars().all()
        }
        return [
            {
                "id": d.id,
                "person_id": d.person_id,
                "person": people.get(d.person_id),
                "week_start": d.week_start,
                "sent_at": d.sent_at.isoformat() if d.sent_at else None,
                "payload": d.payload,
            }
            for d in rows
        ]
