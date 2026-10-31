"""Pipeline orchestration: ingest → normalize → extract → resolve → retrieve → judge."""
import logging

from ..models import Meeting, Utterance, Decision, ActionItem, Conflict
from ..services.extract import extract
from ..services.conflict import retrieve_candidates, judge_pair, classify_conflict
from ..services.people import resolve_or_create_person, person_name_map

log = logging.getLogger(__name__)


async def run_pipeline(meeting_id: str, db) -> dict:
    """Run the full extraction + conflict pipeline for a meeting.

    Returns a payload matching the review screen contract.
    """
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise ValueError(f"meeting {meeting_id} not found")

    import sqlalchemy as sa
    utt_result = await db.execute(
        sa.select(Utterance).where(Utterance.meeting_id == meeting_id).order_by(Utterance.seq)
    )
    utterances = utt_result.scalars().all()
    if not utterances:
        raise ValueError("no utterances for meeting")

    # Resolve speaker labels → people
    participants = sorted({u.speaker_label for u in utterances if u.speaker_label})
    for u in utterances:
        if u.speaker_label and not u.person_id:
            person = await resolve_or_create_person(db, u.speaker_label)
            if person:
                u.person_id = person.id
    await db.commit()  # Release DB transaction before LLM network latency

    # Extract
    raw = await extract(
        utterances=utterances,
        meeting_title=meeting.title,
        started_at=meeting.started_at,
        timezone=meeting.timezone or "Asia/Kolkata",
        participants=participants,
    )

    # Persist extracted decisions / action items (with owner resolution)
    decisions = []
    for d in raw.get("decisions", []):
        decided_by_person = await resolve_or_create_person(db, d.get("decided_by"))
        dec = Decision(
            meeting_id=meeting_id,
            statement=d["statement"],
            topic=d.get("topic"),
            entities=d.get("entities", []),
            rationale=d.get("rationale"),
            decided_by=decided_by_person.id if decided_by_person else None,
            commitment_strength=d.get("commitment_strength", "firm"),
            confidence=d.get("confidence"),
            evidence=d.get("evidence", []),
            status="needs_review",
            decided_at=meeting.started_at,
        )
        db.add(dec)
        decisions.append(dec)

    items = []
    for a in raw.get("action_items", []):
        owner_person = await resolve_or_create_person(db, a.get("owner"))
        flags = [f for f in (a.get("flags") or []) if f not in ("needs_owner", "needs_deadline")]
        if not owner_person:
            flags.append("needs_owner")
        if not a.get("due_date"):
            flags.append("needs_deadline")
        item = ActionItem(
            meeting_id=meeting_id,
            title=a["title"],
            description=a.get("description"),
            owner_id=owner_person.id if owner_person else None,
            owner_source=a.get("owner_source"),
            due_date=a.get("due_date"),
            due_phrase=a.get("due_phrase"),
            correction_note=a.get("correction_note"),
            flags=flags,
            confidence=a.get("confidence"),
            evidence=a.get("evidence", []),
            status="needs_review",
        )
        db.add(item)
        items.append(item)

    await db.flush()

    # Retrieve prior decisions from memory ledger
    prior_result = await db.execute(
        sa.select(Decision).where(
            Decision.status.in_(["active", "approved"]),
            Decision.meeting_id != meeting_id,
        )
    )
    prior_rows = prior_result.scalars().all()
    prior_decisions = [
        {
            "id": d.id,
            "statement": d.statement,
            "topic": d.topic,
            "entities": d.entities,
            "decided_by": d.decided_by,
            "decided_at": d.decided_at.isoformat() if d.decided_at else None,
            "evidence": d.evidence,
        }
        for d in prior_rows
    ]

    new_decisions = [
        {
            "id": d.id,
            "statement": d.statement,
            "topic": d.topic,
            "entities": d.entities,
            "decided_by": d.decided_by,
            "decided_at": d.decided_at.isoformat() if d.decided_at else None,
            "evidence": d.evidence,
        }
        for d in decisions
    ]

    pairs = retrieve_candidates(new_decisions, prior_decisions)
    conflicts = []
    for nd, pd in pairs:
        try:
            verdict = await judge_pair(nd, pd)
        except Exception as e:
            log.warning("Conflict judge failed for %s vs %s: %s", nd["id"], pd["id"], e)
            continue
        relation = verdict.get("relation") or "unrelated"
        if relation == "unrelated":
            continue
        severity = classify_conflict(relation, float(verdict.get("confidence") or 0))
        conf = Conflict(
            type=relation,
            new_decision_id=nd["id"],
            prior_decision_id=pd["id"],
            relation=relation,
            confidence=verdict.get("confidence"),
            rationale=verdict.get("rationale"),
            new_quote=verdict.get("new_evidence_quote"),
            prior_quote=verdict.get("prior_evidence_quote"),
            severity=severity,
        )
        db.add(conf)
        conflicts.append(conf)

    meeting.status = "extracted"
    await db.commit()

    names = await person_name_map(
        db,
        [a.owner_id for a in items] + [d.decided_by for d in decisions],
    )

    return {
        "meeting_id": meeting_id,
        "decisions": [
            {
                "id": d.id,
                "statement": d.statement,
                "topic": d.topic,
                "decided_by": names.get(d.decided_by) if d.decided_by else None,
                "commitment_strength": d.commitment_strength,
                "confidence": d.confidence,
                "evidence": d.evidence,
                "status": d.status,
            }
            for d in decisions
        ],
        "action_items": [
            {
                "id": a.id,
                "title": a.title,
                "owner": names.get(a.owner_id) if a.owner_id else None,
                "owner_id": a.owner_id,
                "due_date": a.due_date,
                "due_phrase": a.due_phrase,
                "flags": a.flags,
                "confidence": a.confidence,
                "evidence": a.evidence,
                "correction_note": a.correction_note,
                "status": a.status,
            }
            for a in items
        ],
        "conflicts": [
            {
                "id": c.id,
                "type": c.type,
                "relation": c.relation,
                "confidence": c.confidence,
                "rationale": c.rationale,
                "new_quote": c.new_quote,
                "prior_quote": c.prior_quote,
                "severity": c.severity,
                "new_decision_id": c.new_decision_id,
                "prior_decision_id": c.prior_decision_id,
            }
            for c in conflicts
        ],
    }
