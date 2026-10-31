"""Meeting ingestion routes (paste / upload / voice recap)."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlalchemy as sa
from sqlalchemy import select

from ..db import get_db_cm as get_db
from ..models import Meeting, Utterance, Person
from ..services.ingest import build_utterances, normalize_transcript
from ..services.pipeline import run_pipeline

router = APIRouter(prefix="/meetings", tags=["Meetings"])


class IngestTextRequest(BaseModel):
    title: str
    text: str
    started_at: str | None = None
    timezone: str = "Asia/Kolkata"
    source: str = "paste"


@router.get("/")
async def list_meetings():
    """List all meetings (for the UI meetings list page)."""
    async with get_db() as db:
        result = await db.execute(select(Meeting))
        meetings = [
            {
                "id": m.id,
                "title": m.title,
                "started_at": m.started_at.isoformat(),
                "timezone": m.timezone,
                "source": m.source,
                "status": m.status,
            }
            for m in result.scalars().all()
        ]
        return meetings


@router.post("/import")
@router.post("/import/text")
async def import_text(req: IngestTextRequest):
    async with get_db() as db:
        try:
            started = datetime.fromisoformat(req.started_at) if req.started_at else datetime.now(tz=timezone.utc)
            meeting_id = str(uuid.uuid4())
            meeting = Meeting(
                id=meeting_id,
                title=req.title,
                started_at=started,
                timezone=req.timezone,
                source=req.source,
                source_ref=None,
                status="ingested",
            )
            db.add(meeting)
            utterances = build_utterances(meeting_id, req.text)
            db.add_all(utterances)
            await db.commit()

            return {"meeting_id": meeting_id, "utterances": len(utterances)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/{meeting_id}/extract")
async def extract_meeting(meeting_id: str):
    async with get_db() as db:
        try:
            result = await run_pipeline(meeting_id, db)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")
        return result


@router.get("/{meeting_id}/review")
async def review_meeting(meeting_id: str):
    async with get_db() as db:
        m = await db.get(Meeting, meeting_id)
        if not m:
            raise HTTPException(status_code=404, detail="meeting not found")
        from sqlalchemy import select as _select
        from ..models import Decision, ActionItem, Conflict
        from ..services.people import person_name_map

        decs = (await db.execute(_select(Decision).where(Decision.meeting_id == meeting_id))).scalars().all()
        items = (await db.execute(_select(ActionItem).where(ActionItem.meeting_id == meeting_id))).scalars().all()
        confs = (await db.execute(_select(Conflict).where(Conflict.new_decision_id.in_(
            [d.id for d in decs] or ["__none__"])))).scalars().all()
        names = await person_name_map(
            db,
            [a.owner_id for a in items] + [d.decided_by for d in decs],
        )
        return {
            "meeting": {
                "id": m.id, "title": m.title, "started_at": m.started_at.isoformat(),
                "timezone": m.timezone, "status": m.status,
            },
            "decisions": [
                {"id": d.id, "statement": d.statement, "topic": d.topic,
                 "decided_by": names.get(d.decided_by) if d.decided_by else None,
                 "commitment_strength": d.commitment_strength, "confidence": d.confidence,
                 "evidence": d.evidence, "status": d.status}
                for d in decs
            ],
            "action_items": [
                {"id": a.id, "title": a.title,
                 "owner": names.get(a.owner_id) if a.owner_id else None,
                 "owner_id": a.owner_id, "due_date": a.due_date,
                 "due_phrase": a.due_phrase, "flags": a.flags or [], "confidence": a.confidence,
                 "evidence": a.evidence, "correction_note": a.correction_note,
                 "status": a.status, "external_url": a.external_url}
                for a in items
            ],
            "conflicts": [
                {"id": c.id, "type": c.type, "relation": c.relation, "confidence": c.confidence,
                 "rationale": c.rationale, "new_quote": c.new_quote, "prior_quote": c.prior_quote,
                 "severity": c.severity, "new_decision_id": c.new_decision_id,
                 "prior_decision_id": c.prior_decision_id, "resolution": c.resolution}
                for c in confs
            ],
        }