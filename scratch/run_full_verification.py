import sys
sys.stdout.reconfigure(encoding='utf-8')
import httpx
import json

m1_text = """Lokanath: Good morning everyone. Let's start with the product planning discussion for the Followthrough project. Our goal for this sprint is to launch the first working version by November 15th.
Priya: I think the first priority should be the transcript ingestion and decision extraction module. Without that, the rest of the workflow won't work.
Lokanath: Agreed. Let's make transcript ingestion the first priority. Priya, you own the transcript ingestion module. Please complete it by November 5th.
Priya: Sure, I'll take ownership of that.
Lokanath: Rahul, can you handle the task tracker integration?
Rahul: Yes. I'll integrate the task tracker and make sure tasks can be created automatically after confirmation. I'll complete it by November 7th.
Lokanath: Good. Anita, please work on the weekly digest functionality. I want every team member to receive a summary of their open tasks every Friday.
Anita: Okay. I'll complete the weekly digest by November 10th.
Lokanath: One more important decision: nothing should be automatically posted to the task tracker without a human confirmation. Even if the AI extracts an action item correctly, the user must confirm it before creating the task.
Priya: Understood.
Lokanath: And let's use the existing PostgreSQL database for storing meeting memory and decisions.
Rahul: Okay, I'll use PostgreSQL for that."""

client = httpx.Client(timeout=90.0)

print("=== STEP 1: IMPORT & EXTRACT MEETING 1 ===")
r1 = client.post('http://127.0.0.1:8000/meetings/import', json={'title': 'Meeting 1 — Product Planning Meeting', 'text': m1_text})
m1_id = r1.json()['meeting_id']
print(f"Meeting 1 ID: {m1_id}")

r1_ext = client.post(f'http://127.0.0.1:8000/meetings/{m1_id}/extract')
d1 = r1_ext.json()

print(f"\nExtracted Decisions ({len(d1.get('decisions', []))}):")
for d in d1.get('decisions', []):
    print(f"  • [{d.get('topic') or 'General'}] {d['statement']} (By: {d.get('decided_by')})")

print(f"\nTracked Action Items ({len(d1.get('action_items', []))}):")
for a in d1.get('action_items', []):
    print(f"  • Task: {a['title']}")
    print(f"    Owner: {a.get('owner')} | Due Date: {a.get('due_date')} | Flags: {a.get('flags')}")

print("\n=== STEP 2: CONFIRM & POST MEETING 1 (ACTIVATE MEMORY LEDGER) ===")
r_bulk = client.post('http://127.0.0.1:8000/review/bulk-approve', json={'meeting_id': m1_id})
print(f"Bulk approved: {r_bulk.json()}")

r_conf = client.post(f'http://127.0.0.1:8000/meetings/{m1_id}/confirm')
print(f"Confirmed & posted tasks: {len(r_conf.json().get('posted', []))}")

print("\n=== STEP 3: IMPORT & EXTRACT MEETING 2 (CONTRADICTION) ===")
m2_text = """Lokanath: Welcome everyone to the tech architecture sync. In our previous meeting we decided on PostgreSQL, but based on our nested JSON transcript schema, we decided to switch to MongoDB Atlas as our database layer for meeting memory.
Rahul: Got it. I will migrate the schemas and update the connection drivers to MongoDB by November 8th.
Priya: I'll update the ingestion pipeline to persist the raw JSON directly to MongoDB by November 6th."""

r2 = client.post('http://127.0.0.1:8000/meetings/import', json={'title': 'Meeting 2 — Tech Architecture Sync', 'text': m2_text})
m2_id = r2.json()['meeting_id']
print(f"Meeting 2 ID: {m2_id}")

r2_ext = client.post(f'http://127.0.0.1:8000/meetings/{m2_id}/extract')
d2 = r2_ext.json()

print(f"\nExtracted Decisions ({len(d2.get('decisions', []))}):")
for d in d2.get('decisions', []):
    print(f"  • [{d.get('topic') or 'General'}] {d['statement']}")

print(f"\nTracked Action Items ({len(d2.get('action_items', []))}):")
for a in d2.get('action_items', []):
    print(f"  • Task: {a['title']} | Owner: {a.get('owner')} | Due: {a.get('due_date')} | Flags: {a.get('flags')}")

print(f"\nDetected Conflicts ({len(d2.get('conflicts', []))}):")
for c in d2.get('conflicts', []):
    print(f"  🚨 Relation: {c.get('relation')} (Severity: {c.get('severity')}, Confidence: {c.get('confidence')})")
    print(f"     New Quote:   \"{c.get('new_quote')}\"")
    print(f"     Prior Quote: \"{c.get('prior_quote')}\"")
    print(f"     Rationale:   {c.get('rationale')}")

