import urllib.request
import json

m_id = '4725679a-9b1b-4e7c-9b7c-463b6b0bfb70'
req = urllib.request.Request(
    'http://127.0.0.1:3001/api/review/bulk-approve',
    data=json.dumps({'meeting_id': m_id}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
res = json.loads(urllib.request.urlopen(req).read().decode())
print('Bulk approve result:', res)

req2 = urllib.request.Request(
    f'http://127.0.0.1:3001/api/meetings/{m_id}/confirm',
    data=json.dumps({'meeting_id': m_id}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
res2 = json.loads(urllib.request.urlopen(req2).read().decode())
print('Posted items count:', len(res2.get('posted_items', [])))
for item in res2.get('posted_items', []):
    print(f"  Posted Task: {item.get('title')} -> {item.get('external_url')}")

