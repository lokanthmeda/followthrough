import httpx
import time

models_to_test = [
    "auto",
    "llama-instant",
    "qwen2.5-7b-instruct",
    "llama-3.2-3b",
    "gemini-2.5-flash-lite",
    "claude-haiku-4.5",
]

client = httpx.Client(timeout=15.0)
headers = {'Authorization': 'Bearer freellmapi-bb8abf6416b357ffb031f17050fc992adef709aedd98b28e'}

for m in models_to_test:
    t0 = time.time()
    try:
        r = client.post(
            'http://127.0.0.1:31415/v1/chat/completions',
            headers=headers,
            json={'model': m, 'messages': [{'role': 'user', 'content': 'Say ping'}]}
        )
        elapsed = round(time.time() - t0, 2)
        if r.status_code == 200:
            resp_txt = r.json()['choices'][0]['message']['content'].strip()
            print(f"[OK] {m:25} in {elapsed}s -> {resp_txt[:30]}")
        else:
            print(f"[ERR {r.status_code}] {m:25} in {elapsed}s")
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        print(f"[TIMEOUT] {m:25} in {elapsed}s")

