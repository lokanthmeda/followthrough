import httpx
import json

transcript = """Lokanath:
Good morning everyone. Let's start with the product planning discussion for the Followthrough project.
Our goal for this sprint is to launch the first working version by November 15th.

Priya:
I think the first priority should be the transcript ingestion and decision extraction module. Without that, the rest of the workflow won't work.

Lokanath:
Agreed. Let's make transcript ingestion the first priority.
Priya, you own the transcript ingestion module. Please complete it by November 5th.

Priya:
Sure, I'll take ownership of that.

Lokanath:
Rahul, can you handle the task tracker integration?

Rahul:
Yes. I'll integrate the task tracker and make sure tasks can be created automatically after confirmation.
I'll complete it by November 7th.

Lokanath:
Good.
Anita, please work on the weekly digest functionality. I want every team member to receive a summary of their open tasks every Friday.

Anita:
Okay. I'll complete the weekly digest by November 10th.

Lokanath:
One more important decision: nothing should be automatically posted to the task tracker without a human confirmation.
Even if the AI extracts an action item correctly, the user must confirm it before creating the task.

Priya:
Understood.

Lokanath:
And let's use the existing PostgreSQL database for storing meeting memory and decisions.

Rahul:
Okay, I'll use PostgreSQL for that.
"""

schema = """{
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

prompt = f"""You extract decisions and action items from a meeting transcript.
Be exhaustive: extract EVERY distinct decision and action item mentioned.

Rules:
1. DECISIONS: high-level agreements made by the group (e.g. priorities, architectural choices like database, process rules like human confirmation).
2. ACTION ITEMS: specific tasks assigned to or committed to by individuals (e.g. Priya building transcript ingestion, Rahul integrating task tracker, Anita building weekly digest).
3. Do NOT invent owners or deadlines. If an owner is named in the transcript (e.g. Priya, Rahul, Anita), set 'owner' to their name.
4. If a deadline is mentioned (e.g. November 5th, November 7th, November 10th), set 'due_date' (e.g. 2026-11-05) and 'due_phrase'.
5. Only include flags like 'needs_owner' or 'needs_deadline' if they are truly missing. When owner and due_date are present, flags MUST be an empty array [].
6. Every item must have verbatim evidence quote.
7. Output ONLY valid JSON matching this schema:
{schema}

TRANSCRIPT:
{transcript}"""

client = httpx.Client(timeout=45.0)
resp = client.post(
    'http://127.0.0.1:31415/v1/chat/completions',
    headers={'Authorization': 'Bearer freellmapi-bb8abf6416b357ffb031f17050fc992adef709aedd98b28e'},
    json={'model': 'auto', 'messages': [{'role': 'user', 'content': prompt}]}
)
print("STATUS:", resp.status_code)
content = resp.json()['choices'][0]['message']['content']
print("RESPONSE:\n", content)

