import httpx
import json

# Prior decision from Meeting 1:
prior_decision = {
    "statement": "Let's use the existing PostgreSQL database for storing meeting memory and decisions.",
    "topic": "Database choice",
    "entities": [{"type": "product", "value": "PostgreSQL"}],
    "decided_by": "Lokanath",
    "decided_at": "2026-10-31T10:00:00",
    "evidence": [{"quote": "And let's use the existing PostgreSQL database for storing meeting memory and decisions."}]
}

# New decision from Meeting 2:
new_decision = {
    "statement": "We decided to switch to MongoDB Atlas as our database layer for meeting memory.",
    "topic": "Database choice",
    "entities": [{"type": "product", "value": "MongoDB Atlas"}],
    "decided_by": "Lokanath",
    "decided_at": "2026-10-31T14:00:00",
    "evidence": [{"quote": "we decided to switch to MongoDB Atlas as our database layer for meeting memory."}]
}

JUDGE_PROMPT = """You compare a NEW decision with a PRIOR decision from an earlier meeting.

NEW:   "{new_statement}"  — {new_speaker}, {new_date}. Quote: "{new_quote}"
PRIOR: "{prior_statement}" — {prior_speaker}, {prior_date}. Quote: "{prior_quote}"

Classify relation:
- contradicts: both cannot be true at the same time (e.g., choice of primary database, conflicting rules)
- supersedes: the new decision changes a parameter (date, number, scope, owner, vendor) of the prior one, replacing it
- duplicate: same decision restated
- refines: adds detail without conflicting
- unrelated: different subject

Ground your rationale in the two quotes. Output JSON only:
{{
  "relation": "contradicts|supersedes|duplicate|refines|unrelated",
  "confidence": 0.95,
  "same_subject": true,
  "rationale": "Clear explanation of how the new decision impacts or conflicts with the prior decision",
  "new_evidence_quote": "{new_quote}",
  "prior_evidence_quote": "{prior_quote}",
  "suggested_resolution": "supersede|keep_old|keep_both|defer"
}}"""

user = JUDGE_PROMPT.format(
    new_statement=new_decision["statement"],
    new_speaker=new_decision["decided_by"],
    new_date=new_decision["decided_at"],
    new_quote=new_decision["evidence"][0]["quote"],
    prior_statement=prior_decision["statement"],
    prior_speaker=prior_decision["decided_by"],
    prior_date=prior_decision["decided_at"],
    prior_quote=prior_decision["evidence"][0]["quote"],
)

client = httpx.Client(timeout=30.0)
resp = client.post(
    'http://127.0.0.1:31415/v1/chat/completions',
    headers={'Authorization': 'Bearer freellmapi-bb8abf6416b357ffb031f17050fc992adef709aedd98b28e'},
    json={'model': 'auto', 'messages': [
        {'role': 'system', 'content': 'You are a conservative conflict judge. Output only JSON.'},
        {'role': 'user', 'content': user}
    ]}
)
print("STATUS:", resp.status_code)
print(resp.json()['choices'][0]['message']['content'])

