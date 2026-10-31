import httpx
import json

transcript = """[0] Lokanath: Good morning everyone. Let's start with the product planning discussion for the Followthrough project. Our goal for this sprint is to launch the first working version by November 15th.
[1] Priya: I think the first priority should be the transcript ingestion and decision extraction module. Without that, the rest of the workflow won't work.
[2] Lokanath: Agreed. Let's make transcript ingestion the first priority. Priya, you own the transcript ingestion module. Please complete it by November 5th.
[3] Priya: Sure, I'll take ownership of that.
[4] Lokanath: Rahul, can you handle the task tracker integration?
[5] Rahul: Yes. I'll integrate the task tracker and make sure tasks can be created automatically after confirmation. I'll complete it by November 7th.
[6] Lokanath: Good. Anita, please work on the weekly digest functionality. I want every team member to receive a summary of their open tasks every Friday.
[7] Anita: Okay. I'll complete the weekly digest by November 10th.
[8] Lokanath: One more important decision: nothing should be automatically posted to the task tracker without a human confirmation. Even if the AI extracts an action item correctly, the user must confirm it before creating the task.
[9] Priya: Understood.
[10] Lokanath: And let's use the existing PostgreSQL database for storing meeting memory and decisions.
[11] Rahul: Okay, I'll use PostgreSQL for that."""

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
Do NOT output any thoughts, monologue, or commentary. Start immediately with '{{' and output ONLY valid JSON.

Schema:
{schema}

TRANSCRIPT:
{transcript}"""

client = httpx.Client(timeout=45.0)
resp = client.post(
    'http://127.0.0.1:31415/v1/chat/completions',
    headers={'Authorization': 'Bearer freellmapi-bb8abf6416b357ffb031f17050fc992adef709aedd98b28e'},
    json={
        'model': 'auto',
        'messages': [
            {'role': 'system', 'content': 'You are a JSON-only API. You NEVER write markdown text, reasoning, or introductions. You ONLY output raw valid JSON.'},
            {'role': 'user', 'content': prompt}
        ]
    }
)
print("STATUS:", resp.status_code)
content = resp.json()['choices'][0]['message']['content']
print("STARTS WITH:", repr(content[:100]))
print("ENDS WITH:", repr(content[-100:]))

