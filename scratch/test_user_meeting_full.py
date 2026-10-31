import urllib.request
import json

meeting_text = """Lokanath: Good morning everyone. Let's start with the product planning discussion for the Followthrough project. Our goal for this sprint is to launch the first working version by November 15th.
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

data = json.dumps({
    'title': 'Meeting 1 — Product Planning Meeting',
    'text': meeting_text
}).encode('utf-8')

req = urllib.request.Request(
    'http://127.0.0.1:3001/api/meetings/import',
    data=data,
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode('utf-8'))
    meeting_id = res['meeting_id']
    print('Imported meeting:', meeting_id)

req2 = urllib.request.Request(
    f'http://127.0.0.1:3001/api/meetings/{meeting_id}/extract',
    data=b'{}',
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req2, timeout=60) as resp2:
    res2 = json.loads(resp2.read().decode('utf-8'))
    print('Decisions count:', len(res2.get('decisions', [])))
    for d in res2.get('decisions', []):
        print(f"  [Decision] {d.get('statement')}")
    print('Action items count:', len(res2.get('action_items', [])))
    for a in res2.get('action_items', []):
        print(f"  [Task] {a.get('owner')} -> {a.get('title')} (due: {a.get('due_date')}, flags: {a.get('flags')})")

