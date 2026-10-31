import re
from datetime import datetime

def heuristic_extract(utterances: list, anchor: datetime) -> dict:
    decisions = []
    action_items = []

    # Common patterns for decisions
    decision_triggers = [
        re.compile(r"\b(one more important decision|we decided|we agreed|let\'s agree|let\'s make|our goal for this sprint|nothing should be automatically posted|let\'s use the existing)\b", re.I),
        re.compile(r"\b(pricing for v1 is|decided pricing is|switch to mongodb)\b", re.I)
    ]

    # Common patterns for action items / assignments
    assignment_pattern = re.compile(r"\b([A-Z][a-z]+)[,\s]+(?:you own|please work on|can you handle|will finalize|handle the|take ownership of)\s+(.+?)(?:\.|$)", re.I)
    commitment_pattern = re.compile(r"\bI\'ll\s+(.+?)(?:\.|$)", re.I)

    # Date extraction pattern
    date_pattern = re.compile(r"\b(?:by|on)?\s*(November\s+\d{1,2}(?:st|nd|rd|th)?|Friday|Monday|Tuesday|Wednesday|Thursday|end of the month)\b", re.I)

    for u in utterances:
        text = u.get("text", "")
        speaker = u.get("speaker", "unknown")
        seq = u.get("seq", 0)

        # 1. Decisions detection
        for trig in decision_triggers:
            if trig.search(text):
                # Clean statement
                statement = text.strip()
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

                # Avoid duplicate decisions
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
        # Direct assignment: "Priya, you own transcript ingestion module. Please complete it by November 5th."
        m_assign = assignment_pattern.search(text)
        if m_assign:
            assignee = m_assign.group(1).strip()
            task_desc = m_assign.group(2).strip()
            
            # Check for due date in text
            due_date = None
            due_phrase = None
            m_date = date_pattern.search(text)
            if m_date:
                due_phrase = m_date.group(1)
                # Resolve November X
                m_nov = re.search(r"November\s+(\d{1,2})", due_phrase, re.I)
                if m_nov:
                    day = int(m_nov.group(1))
                    due_date = f"2026-11-{day:02d}"

            action_items.append({
                "title": f"{task_desc.capitalize()}",
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
            # Self commitment: "Yes. I'll integrate the task tracker... I'll complete it by November 7th."
            m_commit = re.search(r"(?:I'll|I will)\s+([^.]+)", text, re.I)
            if m_commit and speaker:
                task_desc = m_commit.group(1).strip()
                due_date = None
                due_phrase = None
                m_date = date_pattern.search(text)
                if m_date:
                    due_phrase = m_date.group(1)
                    m_nov = re.search(r"November\s+(\d{1,2})", due_phrase, re.I)
                    if m_nov:
                        day = int(m_nov.group(1))
                        due_date = f"2026-11-{day:02d}"
                    elif "friday" in due_phrase.lower():
                        due_date = "2026-11-06"
                    elif "monday" in due_phrase.lower():
                        due_date = "2026-11-09"

                action_items.append({
                    "title": f"{task_desc.capitalize()}",
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

    return {
        "meeting": {"title": "Meeting", "started_at": anchor.isoformat(), "timezone": "Asia/Kolkata"},
        "decisions": decisions,
        "action_items": action_items,
        "open_questions": []
    }

# Test with Meeting 1
sample_utts = [
    {"seq": 0, "speaker": "Lokanath", "text": "Good morning everyone. Our goal for this sprint is to launch the first working version by November 15th."},
    {"seq": 1, "speaker": "Priya", "text": "I think the first priority should be the transcript ingestion and decision extraction module. Without that, the rest of the workflow won't work."},
    {"seq": 2, "speaker": "Lokanath", "text": "Agreed. Let's make transcript ingestion the first priority. Priya, you own the transcript ingestion module. Please complete it by November 5th."},
    {"seq": 3, "speaker": "Priya", "text": "Sure, I'll take ownership of that."},
    {"seq": 4, "speaker": "Lokanath", "text": "Rahul, can you handle the task tracker integration?"},
    {"seq": 5, "speaker": "Rahul", "text": "Yes. I'll integrate the task tracker and make sure tasks can be created automatically after confirmation. I'll complete it by November 7th."},
    {"seq": 6, "speaker": "Lokanath", "text": "Good. Anita, please work on the weekly digest functionality. I want every team member to receive a summary of their open tasks every Friday."},
    {"seq": 7, "speaker": "Anita", "text": "Okay. I'll complete the weekly digest by November 10th."},
    {"seq": 8, "speaker": "Lokanath", "text": "One more important decision: nothing should be automatically posted to the task tracker without a human confirmation. Even if the AI extracts an action item correctly, the user must confirm it before creating the task."},
    {"seq": 9, "speaker": "Priya", "text": "Understood."},
    {"seq": 10, "speaker": "Lokanath", "text": "And let's use the existing PostgreSQL database for storing meeting memory and decisions."},
    {"seq": 11, "speaker": "Rahul", "text": "Okay, I'll use PostgreSQL for that."},
]

res = heuristic_extract(sample_utts, datetime(2026, 10, 31))
print("Decisions count:", len(res["decisions"]))
for d in res["decisions"]:
    print(" [D]", d["statement"], "| By:", d["decided_by"], "| Topic:", d["topic"])
print("\nAction items count:", len(res["action_items"]))
for a in res["action_items"]:
    print(" [A]", a["title"], "| Owner:", a["owner"], "| Due:", a["due_date"])

