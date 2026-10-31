"""Voice command routes (PRD §5.3 Channel C)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..db import get_db_cm as get_db
from ..models import ActionItem, Conflict
from ..services.command import parse_command

router = APIRouter(prefix="/review", tags=["Voice Commands"])


class CommandRequest(BaseModel):
    meeting_id: str
    dictation: str


@router.post("/command")
async def voice_command(req: CommandRequest):
    async with get_db() as db:
        items = (await db.execute(select(ActionItem).where(
            ActionItem.meeting_id == req.meeting_id
        ))).scalars().all()
        conflicts = (await db.execute(select(Conflict).where(
            Conflict.new_decision_id.in_(
                [i.id for i in items]  # placeholder
            )
        ))).scalars().all()

        item_list = [{"id": i.id, "title": i.title} for i in items]
        conf_list = [{"id": c.id, "rationale": c.rationale} for c in conflicts]

        try:
            ops = await parse_command(req.dictation, item_list, conf_list)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Command parse failed: {e}")

        return {"proposed_ops": ops.get("ops", []), "clarify": ops.get("clarify")}