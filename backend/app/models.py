"""SQLAlchemy models mirroring the PRD data model (§9)."""
import uuid
from datetime import datetime
from sqlalchemy import Column, Text, Integer, Boolean, Float, JSON, ForeignKey, UniqueConstraint, Index, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, String

from .db import Base


# Use plain String for SQLite compatibility; UUID handled as text
def _uuid():
    return str(uuid.uuid4())


class Person(Base):
    __tablename__ = "people"
    id = Column(Text, primary_key=True, default=_uuid)
    name = Column(Text, nullable=False)
    email = Column(Text, unique=True, nullable=True)
    aliases = Column(JSON, default=list)
    tracker_user_id = Column(Text, nullable=True)
    slack_user_id = Column(Text, nullable=True)
    timezone = Column(Text, default="Asia/Kolkata")
    created_at = Column(DateTime, default=datetime.utcnow)


class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(Text, primary_key=True, default=_uuid)
    title = Column(Text, nullable=False)
    started_at = Column(DateTime, nullable=False)
    timezone = Column(Text, default="Asia/Kolkata")
    source = Column(Text, nullable=False)   # wispr_meeting | voice_recap | paste | upload
    source_ref = Column(Text, nullable=True)
    series_id = Column(Text, nullable=True)
    status = Column(Text, default="ingested")
    organizer_id = Column(Text, ForeignKey("people.id"), nullable=True)
    __table_args__ = (UniqueConstraint("source", "source_ref", name="uq_meeting_source_ref"),)


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"
    meeting_id = Column(Text, ForeignKey("meetings.id"), primary_key=True)
    person_id = Column(Text, ForeignKey("people.id"), primary_key=True)
    role = Column(Text, nullable=True)
    spoke = Column(Boolean, default=False)


class Utterance(Base):
    __tablename__ = "utterances"
    id = Column(Text, primary_key=True, default=_uuid)
    meeting_id = Column(Text, ForeignKey("meetings.id"), nullable=False)
    seq = Column(Integer, nullable=False)
    speaker_label = Column(Text, nullable=True)
    person_id = Column(Text, ForeignKey("people.id"), nullable=True)
    start_ms = Column(Integer, nullable=True)
    text_raw = Column(Text, nullable=False)
    text_clean = Column(Text, nullable=True)


class Decision(Base):
    __tablename__ = "decisions"
    id = Column(Text, primary_key=True, default=_uuid)
    meeting_id = Column(Text, ForeignKey("meetings.id"), nullable=True)
    statement = Column(Text, nullable=False)
    topic = Column(Text, nullable=True)
    entities = Column(JSON, default=list)
    rationale = Column(Text, nullable=True)
    decided_by = Column(Text, ForeignKey("people.id"), nullable=True)
    commitment_strength = Column(Text, default="firm")
    confidence = Column(Float, nullable=True)
    evidence = Column(JSON, nullable=False, default=list)
    status = Column(Text, default="needs_review")
    supersedes_id = Column(Text, ForeignKey("decisions.id"), nullable=True)
    embedding = Column(JSON, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Text, ForeignKey("people.id"), nullable=True)


class ActionItem(Base):
    __tablename__ = "action_items"
    id = Column(Text, primary_key=True, default=_uuid)
    meeting_id = Column(Text, ForeignKey("meetings.id"), nullable=True)
    derived_from_decision_id = Column(Text, ForeignKey("decisions.id"), nullable=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Text, ForeignKey("people.id"), nullable=True)
    owner_source = Column(Text, nullable=True)
    due_date = Column(String(10), nullable=True)      # YYYY-MM-DD
    due_phrase = Column(Text, nullable=True)
    correction_note = Column(Text, nullable=True)
    flags = Column(JSON, default=list)
    confidence = Column(Float, nullable=True)
    evidence = Column(JSON, nullable=False, default=list)
    status = Column(Text, default="needs_review")
    dedupe_key = Column(Text, unique=True, nullable=True)
    external_system = Column(Text, nullable=True)
    external_id = Column(Text, nullable=True)
    external_url = Column(Text, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class Conflict(Base):
    __tablename__ = "conflicts"
    id = Column(Text, primary_key=True, default=_uuid)
    type = Column(Text, nullable=True)
    new_decision_id = Column(Text, ForeignKey("decisions.id"), nullable=True)
    prior_decision_id = Column(Text, ForeignKey("decisions.id"), nullable=True)
    new_item_id = Column(Text, ForeignKey("action_items.id"), nullable=True)
    relation = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    rationale = Column(Text, nullable=True)
    new_quote = Column(Text, nullable=True)
    prior_quote = Column(Text, nullable=True)
    severity = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    resolved_by = Column(Text, ForeignKey("people.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)


class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(Text, primary_key=True, default=_uuid)
    action_item_id = Column(Text, ForeignKey("action_items.id"), nullable=False)
    kind = Column(Text, nullable=True)
    send_at = Column(DateTime, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    channel = Column(Text, nullable=True)
    status = Column(Text, default="scheduled")
    __table_args__ = (UniqueConstraint("action_item_id", "kind", name="uq_reminder_item_kind"),)


class Digest(Base):
    __tablename__ = "digests"
    id = Column(Text, primary_key=True, default=_uuid)
    person_id = Column(Text, ForeignKey("people.id"), nullable=False)
    week_start = Column(String(10), nullable=False)
    payload = Column(JSON, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint("person_id", "week_start", name="uq_digest_person_week"),)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    at = Column(DateTime, default=datetime.utcnow)
    actor = Column(Text, nullable=True)
    action = Column(Text, nullable=True)
    entity = Column(Text, nullable=True)
    entity_id = Column(Text, nullable=True)
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=True)


# (DateTime imported above)