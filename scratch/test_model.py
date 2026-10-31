import httpx
client = httpx.Client(timeout=30.0)
r = client.post(
    'http://127.0.0.1:31415/v1/chat/completions',
    headers={'Authorization': 'Bearer freellmapi-bb8abf6416b357ffb031f17050fc992adef709aedd98b28e'},
    json={'model': 'gemini-flash', 'messages': [{'role': 'user', 'content': 'Output valid JSON {"status": "working"}'}]}
)
print('STATUS:', r.status_code)
print('CONTENT:', r.json()['choices'][0]['message']['content'])

