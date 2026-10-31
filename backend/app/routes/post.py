"""Confirm & post — the ONLY code path that writes to the tracker (PRD §6.4.5)."""
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..db import get_db_cm as get_db
from ..models import Meeting, ActionItem, Decision, AuditLog, Conflict
from ..adapters.tracker import get_adapter, dedupe_key
from ..services.reminders import schedule_reminders_for_item, process_due_reminders
from ..services.people import person_name_map

router = APIRouter(prefix="/meetings", tags=["Post"])


class ConfirmRequest(BaseModel):
    meeting_id: str | None = None


@router.post("/{meeting_id}/post-preview")
async def post_preview(meeting_id: str):
    async with get_db() as db:
        m = await db.get(Meeting, meeting_id)
        if not m:
            raise HTTPException(status_code=404, detail="meeting not found")
        items = (await db.execute(select(ActionItem).where(
            ActionItem.meeting_id == meeting_id, ActionItem.status == "approved"
        ))).scalars().all()
        names = await person_name_map(db, [i.owner_id for i in items])
        return {
            "meeting": {"id": m.id, "title": m.title},
            "items": [
                {
                    "id": i.id,
                    "title": i.title,
                    "owner": names.get(i.owner_id) if i.owner_id else None,
                    "due_date": i.due_date,
                    "dedupe_key": i.dedupe_key,
                }
                for i in items
            ],
            "count": len(items),
        }


@router.post("/{meeting_id}/confirm")
@router.post("/{meeting_id}/confirm-and-post")
async def confirm_and_post(meeting_id: str, body: ConfirmRequest | None = None):
    """Server-side gate: only approved items are posted. Idempotent."""
    async with get_db() as db:
        m = await db.get(Meeting, meeting_id)
        if not m:
            raise HTTPException(status_code=404, detail="meeting not found")

        # Hard gate: unresolved blocking conflicts
        dec_ids = (await db.execute(
            select(Decision.id).where(Decision.meeting_id == meeting_id)
        )).scalars().all()
        if dec_ids:
            blocking = (await db.execute(select(Conflict).where(
                Conflict.new_decision_id.in_(dec_ids),
                Conflict.severity == "blocking",
                Conflict.resolution.is_(None),
            ))).scalars().first()
            if blocking:
                raise HTTPException(
                    status_code=422,
                    detail="Unresolved blocking conflicts — resolve before posting",
                )

        items = (await db.execute(select(ActionItem).where(
            ActionItem.meeting_id == meeting_id, ActionItem.status == "approved"
        ))).scalars().all()

        adapter = get_adapter()
        posted = []
        failed = []
        reminders_scheduled = 0
        for item in items:
            if item.external_id and item.external_system:
                posted.append({
                    "id": item.id, "external_id": item.external_id,
                    "external_url": item.external_url, "skipped": True,
                })
                continue

            try:
                ref = adapter.create_task({
                    "title": item.title,
                    "description": _issue_description(item, m),
                    "assignee_id": None,
                    "due_date": item.due_date,
                    "label_ids": [],
                    "team_id": None,
                })
                item.external_system = ref.external_system
                item.external_id = ref.external_id
                item.external_url = ref.external_url
                item.status = "posted"
                item.posted_at = datetime.utcnow()
                item.dedupe_key = dedupe_key(meeting_id, item.title, item.owner_id)
                rems = await schedule_reminders_for_item(db, item)
                reminders_scheduled += len(rems)
                posted.append({
                    "id": item.id, "external_id": ref.external_id,
                    "external_url": ref.external_url, "skipped": False,
                })
            except Exception as e:
                failed.append({"id": item.id, "error": str(e)})

        # Commit approved decisions to memory ledger
        decs = (await db.execute(select(Decision).where(
            Decision.meeting_id == meeting_id, Decision.status == "approved"
        ))).scalars().all()
        for d in decs:
            d.status = "active"
            d.approved_at = datetime.utcnow()

        m.status = "committed"
        db.add(AuditLog(
            actor="user", action="meeting.confirm_and_post",
            entity="meeting", entity_id=meeting_id,
            before={"status": "extracted"},
            after={
                "status": "committed",
                "posted": len(posted),
                "failed": len(failed),
                "reminders_scheduled": reminders_scheduled,
                "decisions_activated": len(decs),
            },
        ))
        await db.commit()

        # Deliver any reminders that are already due (e.g. deadlines within 24h)
        reminder_delivery = await process_due_reminders(db)

        return {
            "posted": posted,
            "failed": failed,
            "reminders_scheduled": reminders_scheduled,
            "reminders_sent": reminder_delivery.get("sent", 0),
            "decisions_activated": len(decs),
            "meeting_status": m.status,
        }


def _issue_description(item, meeting) -> str:
    ev = (item.evidence or [{}])
    quote = ev[0].get("quote", "") if ev else ""
    speaker = ev[0].get("speaker", "") if ev else ""
    started = ""
    if meeting.started_at:
        started = meeting.started_at.strftime("%b %d, %Y")
    return (
        f"**From:** {meeting.title} — {started}\n"
        f"**Said by {speaker}:** \"{quote}\"\n"
        f"Meeting & evidence: followthrough.meetings/{meeting.id}"
    )
