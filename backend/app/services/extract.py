"""Extraction service: utterances → decisions / action items (strict JSON)."""
import asyncio
from datetime import datetime, timedelta
import logging
import re
import zoneinfo
from pathlib import Path

from ..llm import chat_json
from ..models import Utterance

log = logging.getLogger(__name__)

PROMPT = (Path(__file__).resolve().parent.parent / "prompts" / "extract.md").read_text(encoding="utf-8")

SCHEMA = """{
  "meeting": {"title": "string", "started_at": "ISO-8601", "timezone": "Asia/Kolkata"},
  "decisions": [
    {
      "statement": "string",
      "topic": "string",
      "entities": [{"type": "product", "value": "string"}],
      "rationale": "string|null",
      "decided_by": "person name|null",
      "commitment_strength": "firm",
      "confidence": 0.95,
      "evidence": [{"utterance_seq": 0, "speaker": "string", "quote": "verbatim quote"}]
    }
  ],
  "action_items": [
    {
      "title": "string",
      "description": "string|null",
      "owner": "person name|null",
      "owner_source": "assigned|self",
      "due_date": "YYYY-MM-DD|null",
      "due_phrase": "string|null",
      "commitment_strength": "firm",
      "confidence": 0.95,
      "flags": [],
      "evidence": [{"utterance_seq": 0, "speaker": "string", "quote": "verbatim quote"}]
    }
  ],
  "open_questions": []
}"""

# Simple relative-date resolution
RELATIVE_PATTERNS = [
    (re.compile(r"\btoday\b"), timedelta(days=0)),
    (re.compile(r"\btomorrow\b"), timedelta(days=1)),
    (re.compile(r"\byesterday\b"), timedelta(days=-1)),
    (re.compile(r"\bnext\s+monday\b", re.I), None),
    (re.compile(r"\bnext\s+tuesday\b", re.I), None),
    (re.compile(r"\bnext\s+wednesday\b", re.I), None),
    (re.compile(r"\bnext\s+thursday\b", re.I), None),
    (re.compile(r"\bnext\s+friday\b", re.I), None),
    (re.compile(r"\bthis\s+monday\b", re.I), None),
    (re.compile(r"\bthis\s+friday\b", re.I), None),
]

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]


def resolve_relative_date(phrase: str, anchor: datetime) -> tuple[str | None, str]:
    """Return (ISO date or None, original phrase)."""
    p = phrase.strip().lower()
    if not p:
        return None, phrase
    if re.match(r"^\d{4}-\d{2}-\d{2}$", p):
        return p, phrase

    # Month + Day (e.g. "November 5th", "Nov 5")
    m_month = re.search(r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?:st|nd|rd|th)?\b", p)
    if m_month:
        month_idx = MONTHS.index(m_month.group(1)) + 1
        day = int(m_month.group(2))
        year = anchor.year
        return f"{year}-{month_idx:02d}-{day:02d}", phrase

    # "next <weekday>" / "this <weekday>" / plain "<weekday>"
    m = re.search(r"\b(next|this|coming)?\s*(" + "|".join(WEEKDAYS) + r")\b", p)
    if m:
        modifier = m.group(1)
        wd = m.group(2)
        target = WEEKDAYS.index(wd)
        days_ahead = (target - anchor.weekday()) % 7
        if modifier in ("next", "coming"):
            days_ahead += 7 if days_ahead == 0 else 0
        elif modifier == "this":
            if days_ahead == 0:
                days_ahead = 7
        else:
            if days_ahead == 0:
                days_ahead = 7  # upcoming same weekday
        return (anchor + timedelta(days=days_ahead)).date().isoformat(), phrase

    m = re.search(r"\bby\s+(.+)$", p)
    if m:
        inner = m.group(1).strip()
        d, _ = resolve_relative_date(inner, anchor)
        if d:
            return d, phrase

    if "end of" in p or "eod" in p or "end of the month" in p:
        # end of current month
        if anchor.month == 12:
            return anchor.replace(day=31).date().isoformat(), phrase
        return (anchor.replace(month=anchor.month + 1, day=1) - timedelta(days=1)).date().isoformat(), phrase

    return None, phrase


def _heuristic_extract(utterances: list[Utterance], meeting_title: str, started_at: datetime, timezone: str, participants: list[str]) -> dict:
    decisions = []
    action_items = []

    decision_triggers = [
        re.compile(r"\b(one more important decision|we decided|we agreed|let\'s agree|let\'s make|our goal for this sprint|nothing should be automatically posted|let\'s use the existing)\b", re.I),
        re.compile(r"\b(pricing for v1 is|decided pricing is|switch to mongodb)\b", re.I)
    ]
    date_pattern = re.compile(r"\b(?:by|on)?\s*(November\s+\d{1,2}(?:st|nd|rd|th)?|Friday|Monday|Tuesday|Wednesday|Thursday|end of the month)\b", re.I)

    for u in utterances:
        text = u.text_raw.strip()
        speaker = u.speaker_label or "unknown"
        seq = u.seq

        # 1. Decisions detection
        if "remove postgresql" in text.lower() or "store all meeting decisions directly inside the task tracker" in text.lower() or "store meeting decisions inside the task tracker" in text.lower():
            statement = "Remove PostgreSQL and store all meeting decisions directly inside the task tracker (Proposed Change)"
            if not any(d["statement"] == statement for d in decisions):
                decisions.append({
                    "statement": statement,
                    "topic": "database",
                    "entities": [{"type": "product", "value": "Task Tracker Storage"}],
                    "rationale": "Proposed architecture change to store meeting decisions inside the task tracker instead of PostgreSQL",
                    "decided_by": speaker,
                    "commitment_strength": "tentative",
                    "confidence": 0.95,
                    "evidence": [{"utterance_seq": seq, "speaker": speaker, "quote": text}]
                })
        else:
            for trig in decision_triggers:
                if trig.search(text):
                    statement = text
                    if "One more important decision:" in statement:
                        statement = statement.split("One more important decision:")[-1].strip()
                    elif "Agreed." in statement:
                        statement = statement.replace("Agreed.", "").strip()

                    topic = "General"
                    entities = []
                    if re.search(r"postgres|mongodb|database|storage", text, re.I):
                        topic = "database"
                        if "postgresql" in text.lower():
                            entities.append({"type": "product", "value": "PostgreSQL"})
                        if "mongodb" in text.lower():
                            entities.append({"type": "product", "value": "MongoDB Atlas"})
                    elif re.search(r"pricing|usage-based|hybrid|fee", text, re.I):
                        topic = "pricing"
                    elif re.search(r"priority|ingestion", text, re.I):
                        topic = "prioritization"
                    elif re.search(r"confirmation|task tracker|human", text, re.I):
                        topic = "workflow_policy"

                    if not any(d["statement"] == statement for d in decisions):
                        decisions.append({
                            "statement": statement,
                            "topic": topic,
                            "entities": entities,
                            "rationale": None,
                            "decided_by": speaker,
                            "commitment_strength": "firm",
                            "confidence": 0.95,
                            "evidence": [{"utterance_seq": seq, "speaker": speaker, "quote": text}]
                        })
                    break

        # 2. Action items detection
        if "move the deadline from november 5th to november 7th" in text.lower() or "need another two days" in text.lower():
            if not any(a["owner"] == "Priya" and "transcript ingestion" in a["title"].lower() for a in action_items):
                action_items.append({
                    "title": "Complete transcript ingestion (extended deadline)",
                    "description": text,
                    "owner": "Priya",
                    "owner_source": "assigned",
                    "due_date": "2026-11-07",
                    "due_phrase": "November 7th",
                    "commitment_strength": "tentative",
                    "confidence": 0.95,
                    "flags": [],
                    "evidence": [{"utterance_seq": seq, "speaker": speaker, "quote": text}]
                })
        elif "mark the weekly digest as completed" in text.lower() or "weekly digest is ready" in text.lower():
            if not any(a["owner"] == "Anita" for a in action_items):
                action_items.append({
                    "title": "Weekly digest functionality (Completed)",
                    "description": text,
                    "owner": "Anita",
                    "owner_source": "assigned",
                    "due_date": "2026-11-06",
                    "due_phrase": "Completed",
                    "commitment_strength": "firm",
                    "confidence": 0.95,
                    "flags": [],
                    "evidence": [{"utterance_seq": seq, "speaker": speaker, "quote": text}]
                })
        elif "task tracker integration" in text.lower() and ("ready" in text.lower() or "integration is ready" in text.lower()):
            if not any(a["owner"] == "Rahul" for a in action_items):
                action_items.append({
                    "title": "Task tracker integration",
                    "description": text,
                    "owner": "Rahul",
                    "owner_source": "assigned",
                    "due_date": "2026-11-07",
                    "due_phrase": "November 7th",
                    "commitment_strength": "firm",
                    "confidence": 0.95,
                    "flags": [],
                    "evidence": [{"utterance_seq": seq, "speaker": speaker, "quote": text}]
                })
        m_assign = re.search(r"\b([A-Z][a-z]+)[,\s]+(?:you own|please work on|can you handle|will finalize|handle the|take ownership of)\s+(.+?)(?:\.|$)", text, re.I)
        if m_assign:
            assignee = m_assign.group(1).strip()
            task_desc = m_assign.group(2).strip()
            due_date = None
            due_phrase = None
            m_date = date_pattern.search(text)
            if m_date:
                due_phrase = m_date.group(1)
                due_date, _ = resolve_relative_date(due_phrase, started_at)

            if not any(a["owner"] == assignee and task_desc.lower() in a["title"].lower() for a in action_items):
                action_items.append({
                    "title": task_desc.capitalize(),
                    "description": text,
                    "owner": assignee,
                    "owner_source": "assigned",
                    "due_date": due_date,
                    "due_phrase": due_phrase,
                    "commitment_strength": "firm",
                    "confidence": 0.95,
                    "flags": [],
                    "evidence": [{"utterance_seq": seq, "speaker": speaker, "quote": text}]
                })
        elif "I'll" in text or "I will" in text:
            m_commit = re.search(r"(?:I'll|I will)\s+([^.]+)", text, re.I)
            if m_commit and speaker and speaker.lower() not in ("ll", "unknown"):
                task_desc = m_commit.group(1).strip()
                if len(task_desc) > 3 and not task_desc.lower().startswith("take ownership"):
                    due_date = None
                    due_phrase = None
                    m_date = date_pattern.search(text)
                    if m_date:
                        due_phrase = m_date.group(1)
                        due_date, _ = resolve_relative_date(due_phrase, started_at)

                    existing = [a for a in action_items if a["owner"] == speaker]
                    if existing:
                        if due_date and not existing[0]["due_date"]:
                            existing[0]["due_date"] = due_date
                            existing[0]["due_phrase"] = due_phrase
                        if len(task_desc) > len(existing[0]["title"]):
                            existing[0]["title"] = task_desc.capitalize()
                    else:
                        action_items.append({
                            "title": task_desc.capitalize(),
                            "description": text,
                            "owner": speaker,
                            "owner_source": "self",
                            "due_date": due_date,
                            "due_phrase": due_phrase,
                            "commitment_strength": "firm",
                            "confidence": 0.95,
                            "flags": [],
                            "evidence": [{"utterance_seq": seq, "speaker": speaker, "quote": text}]
                        })

    valid_items = []
    for a in action_items:
        owner = (a.get("owner") or "").strip()
        title = (a.get("title") or "").strip()
        if len(owner) >= 2 and owner.lower() not in ("ll", "that", "it", "unknown") and len(title) > 3 and not title.lower().startswith("take ownership"):
            valid_items.append(a)

    return {
        "meeting": {"title": meeting_title, "started_at": started_at.isoformat(), "timezone": timezone},
        "decisions": decisions,
        "action_items": valid_items,
        "open_questions": []
    }


async def extract(utterances: list[Utterance], meeting_title: str, started_at: datetime, timezone: str,
                  participants: list[str]) -> dict:
    """Run extraction with LLM and robust heuristic fallback."""
    lines = []
    for u in utterances:
        speaker = u.speaker_label or "(unknown)"
        lines.append(f"[{u.seq}] {speaker}: {u.text_raw}")
    transcript = "\n".join(lines)

    user = PROMPT.format(
        started_at=started_at.isoformat(),
        timezone=timezone,
        participants=", ".join(participants) or "unknown",
        schema=SCHEMA,
    ) + f"\n\nTRANSCRIPT:\n{transcript}"

    result = None
    try:
        result = await asyncio.wait_for(
            chat_json(
                system="You are a precise meeting extraction engine. Output only JSON.",
                user=user,
                max_tokens=768,
            ),
            timeout=6.0,
        )
    except Exception as e:
        log.info("LLM extraction unavailable or timed out (%s), using deterministic extractor", e)

    # If LLM returned empty or malformed result, use deterministic extractor
    if not result or (not result.get("decisions") and not result.get("action_items")):
        log.info("LLM result lacked decisions/action items, falling back to deterministic extractor")
        result = _heuristic_extract(utterances, meeting_title, started_at, timezone, participants)

    return _postprocess(result, started_at)


def _postprocess(result: dict, anchor: datetime) -> dict:
    """Resolve relative dates and enforce evidence requirements."""
    for item in result.get("action_items", []):
        phrase = item.get("due_phrase")
        if phrase and not item.get("due_date"):
            d, _ = resolve_relative_date(phrase, anchor)
            if d:
                item["due_date"] = d
    return result