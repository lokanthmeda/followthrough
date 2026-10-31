import sys
sys.path.insert(0, ".")
import httpx
import traceback
from backend.app.config import settings

endpoint = f"{settings.llm_base_url.rstrip('/')}/v1/chat/completions"
print("Connecting to:", endpoint)
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {settings.llm_api_key}",
}
body = {
    "model": "auto",
    "messages": [
        {"role": "system", "content": "You are a precise meeting extraction engine. Output only JSON."},
        {"role": "user", "content": "Return a JSON object with key hello set to world"},
    ],
    "temperature": 0.1,
    "max_tokens": 4096,
}
client = httpx.Client(timeout=30.0)
try:
    r = client.post(endpoint, json=body, headers=headers)
    print("STATUS:", r.status_code)
    print("RESP:", r.json())
except Exception as e:
    traceback.print_exc()
