import urllib.request
import json

m2_text = """Lokanath: Welcome everyone. In our previous meeting we decided on PostgreSQL, but based on our nested JSON transcript schema, we decided to switch to MongoDB Atlas as our database layer for meeting memory.
Rahul: Got it. I will migrate the schemas and update the connection drivers to MongoDB by November 8th.
Priya: I'll update the ingestion pipeline to persist the raw JSON directly to MongoDB by November 6th."""

data = json.dumps({'title': 'Meeting 2 — Architecture Decision (Conflict Demo)', 'text': m2_text}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:3001/api/meetings/import', data=data, headers={'Content-Type': 'application/json'})
res = json.loads(urllib.request.urlopen(req).read().decode())
meeting_id = res['meeting_id']
print('Meeting 2 ID:', meeting_id)

req2 = urllib.request.Request(f'http://127.0.0.1:3001/api/meetings/{meeting_id}/extract', data=b'{}', headers={'Content-Type': 'application/json'})
res2 = json.loads(urllib.request.urlopen(req2, timeout=20).read().decode())
print('Meeting 2 Decisions:', len(res2.get('decisions', [])))
print('Meeting 2 Conflicts:', len(res2.get('conflicts', [])))
for c in res2.get('conflicts', []):
    print(f"  [CONFLICT {c.get('severity')}] {c.get('relation')} -> {c.get('rationale')}")

