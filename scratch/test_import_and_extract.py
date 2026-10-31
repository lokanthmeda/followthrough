import urllib.request
import json

def test():
    data = json.dumps({
        'title': 'Product Planning Meeting Test',
        'text': "Lokanath: Welcome everyone. Lets plan the launch for Nov 15.\nPriya: Transcript ingestion is first priority by Nov 5.\nRahul: I will integrate task tracker by Nov 7.\nAnita: I will complete weekly digest by Nov 10."
    }).encode('utf-8')
    
    req = urllib.request.Request(
        'http://127.0.0.1:3001/api/meetings/import',
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        print('Import status:', resp.status)
        res = json.loads(resp.read().decode('utf-8'))
        print('Import Response:', res)
        meeting_id = res['meeting_id']

    req2 = urllib.request.Request(
        f'http://127.0.0.1:3001/api/meetings/{meeting_id}/extract',
        data=b'{}',
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req2, timeout=60) as resp2:
        print('Extract status:', resp2.status)
        res2 = json.loads(resp2.read().decode('utf-8'))
        decisions = res2.get('decisions', [])
        action_items = res2.get('action_items', [])
        print(f'Decisions count: {len(decisions)}')
        for d in decisions:
            print(f'  - Decision: {d.get("statement")}')
        print(f'Action items count: {len(action_items)}')
        for a in action_items:
            print(f'  - Action Item: {a.get("owner")} -> {a.get("title")} (due: {a.get("due_date")})')

if __name__ == '__main__':
    test()

