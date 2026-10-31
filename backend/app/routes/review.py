"""Review + confirmation gate (PRD §6.4)."""
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..db import get_db_cm as get_db
from ..models import ActionItem, Decision, Conflict, AuditLog, Meeting
from ..services.people import resolve_or_create_person

router = APIRouter(prefix="/review", tags=["Review"])


class PatchItem(BaseModel):
    title: str | None = None
    owner: str | None = None
    owner_id: str | None = None
    due_date: str | None = None
    due_phrase: str | None = None
    description: str | None = None
    action: str | None = None  # "approve" | "reject"


class PatchDecision(BaseModel):
    action: str | None = None  # "approve" | "reject"
    statement: str | None = None


class ResolveConflict(BaseModel):
    resolution: str  # supersede | keep_old | keep_both | defer


class BulkApprove(BaseModel):
    meeting_id: str
    approve_items: bool = True
    approve_decisions: bool = True


async def _has_unresolved_blocking_for_decision(db, decision_id: str) -> bool:
    confs = await db.execute(select(Conflict).where(
        Conflict.new_decision_id == decision_id,
        Conflict.severity == "blocking",
        Conflict.resolution.is_(None),
    ))
    return confs.scalars().first() is not None


async def _meeting_has_unresolved_blocking(db, meeting_id: str) -> bool:
    dec_ids = (await db.execute(select(Decision.id).where(Decision.meeting_id == meeting_id))).scalars().all()
    if not dec_ids:
        return False
    confs = await db.execute(select(Conflict).where(
        Conflict.new_decision_id.in_(dec_ids),
        Conflict.severity == "blocking",
        Conflict.resolution.is_(None),
    ))
    return confs.scalars().first() is not None


@router.patch("/items/{item_id}")
async def patch_item(item_id: str, body: PatchItem):
    async with get_db() as db:
        item = await db.get(ActionItem, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="item not found")

        before = {c: getattr(item, c) for c in
                  ("title", "owner_id", "due_date", "due_phrase", "description", "status")}

        if body.title is not None:
            item.title = body.title
        if body.description is not None:
            item.description = body.description
        if body.due_date is not None:
            item.due_date = body.due_date
            flags = list(item.flags or [])
            if "needs_deadline" in flags and body.due_date:
                flags = [f for f in flags if f != "needs_deadline"]
                item.flags = flags
        if body.due_phrase is not None:
            item.due_phrase = body.due_phrase
        if body.owner_id is not None:
            item.owner_id = body.owner_id
        if body.owner is not None:
            person = await resolve_or_create_person(db, body.owner)
            item.owner_id = person.id if person else None
            flags = list(item.flags or [])
            if person and "needs_owner" in flags:
                flags = [f for f in flags if f != "needs_owner"]
                item.flags = flags

        if body.action == "approve":
            if item.meeting_id and await _meeting_has_unresolved_blocking(db, item.meeting_id):
                raise HTTPException(
                    status_code=422,
                    detail="Unresolved blocking conflict — resolve conflicts before approving",
                )
            item.status = "approved"
        elif body.action == "reject":
            item.status = "rejected"

        after = {c: getattr(item, c) for c in
                 ("title", "owner_id", "due_date", "due_phrase", "description", "status")}
        db.add(AuditLog(actor="user", action=f"item.{body.action or 'edit'}",
                        entity="action_item", entity_id=item_id, before=before, after=after))
        await db.commit()
        return {"id": item.id, "status": item.status, "owner_id": item.owner_id, "due_date": item.due_date}


@router.patch("/decisions/{decision_id}")
async def patch_decision(decision_id: str, body: PatchDecision):
    async with get_db() as db:
        dec = await db.get(Decision, decision_id)
        if not dec:
            raise HTTPException(status_code=404, detail="decision not found")
        before = {"status": dec.status, "statement": dec.statement}
        if body.statement is not None:
            dec.statement = body.statement
        if body.action == "approve":
            if await _has_unresolved_blocking_for_decision(db, decision_id):
                raise HTTPException(
                    status_code=422,
                    detail="Unresolved blocking conflict on this decision",
                )
            dec.status = "approved"
        elif body.action == "reject":
            dec.status = "rejected"
        after = {"status": dec.status, "statement": dec.statement}
        db.add(AuditLog(actor="user", action=f"decision.{body.action or 'edit'}",
                        entity="decision", entity_id=decision_id, before=before, after=after))
        await db.commit()
        return {"id": dec.id, "status": dec.status}


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(conflict_id: str, body: ResolveConflict):
    async with get_db() as db:
        c = await db.get(Conflict, conflict_id)
        if not c:
            raise HTTPException(status_code=404, detail="conflict not found")
        c.resolution = body.resolution
        c.resolved_at = datetime.utcnow()

        if body.resolution == "supersede" and c.new_decision_id:
            new = await db.get(Decision, c.new_decision_id)
            old = await db.get(Decision, c.prior_decision_id) if c.prior_decision_id else None
            if new:
                new.status = "approved"
            if old:
                old.status = "superseded"
                if new:
                    old.supersedes_id = new.id
        elif body.resolution == "keep_old" and c.new_decision_id:
            new = await db.get(Decision, c.new_decision_id)
            if new:
                new.status = "rejected"
        elif body.resolution == "keep_both":
            c.severity = "info"
            if c.new_decision_id:
                new = await db.get(Decision, c.new_decision_id)
                if new and new.status == "needs_review":
                    new.status = "approved"
        elif body.resolution == "defer":
            c.severity = "possible"

        db.add(AuditLog(actor="user", action="conflict.resolve",
                        entity="conflict", entity_id=conflict_id,
                        before={"resolution": None}, after={"resolution": body.resolution}))
        await db.commit()
        return {"id": conflict_id, "resolution": body.resolution}


@router.post("/bulk-approve")
async def bulk_approve(body: BulkApprove):
    """Approve all reviewable items/decisions for a meeting (after conflicts cleared)."""
    async with get_db() as db:
        m = await db.get(Meeting, body.meeting_id)
        if not m:
            raise HTTPException(status_code=404, detail="meeting not found")
        if await _meeting_has_unresolved_blocking(db, body.meeting_id):
            raise HTTPException(
                status_code=422,
                detail="Unresolved blocking conflicts — resolve them first",
            )

        approved_items = 0
        approved_decs = 0
        if body.approve_items:
            items = (await db.execute(select(ActionItem).where(
                ActionItem.meeting_id == body.meeting_id,
                ActionItem.status == "needs_review",
            ))).scalars().all()
            for item in items:
                item.status = "approved"
                approved_items += 1
        if body.approve_decisions:
            decs = (await db.execute(select(Decision).where(
                Decision.meeting_id == body.meeting_id,
                Decision.status == "needs_review",
            ))).scalars().all()
            for d in decs:
                d.status = "approved"
                approved_decs += 1

        db.add(AuditLog(
            actor="user", action="meeting.bulk_approve", entity="meeting",
            entity_id=body.meeting_id,
            before={}, after={"items": approved_items, "decisions": approved_decs},
        ))
        await db.commit()
        return {"approved_items": approved_items, "approved_decisions": approved_decs}
