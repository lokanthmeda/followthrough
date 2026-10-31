import sys
sys.path.insert(0, ".")
import httpx
from backend.app.config import settings
from backend.app.services.extract import PROMPT, SCHEMA

endpoint = f"{settings.llm_base_url.rstrip('/')}/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {settings.llm_api_key}",
}

user = PROMPT.format(
    started_at="2026-10-31T10:00:00",
    timezone="Asia/Kolkata",
    participants="Anita, Lokanath, Priya, Rahul",
    schema=SCHEMA,
) + """\n\nTRANSCRIPT:
[0] Lokanath: Good morning everyone. Let's start with the product planning discussion for the Followthrough project. Our goal for this sprint is to launch the first working version by November 15th.
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

body = {
    "model": "auto",
    "messages": [
        {"role": "user", "content": f"You are a precise meeting extraction engine.\n\n{user}\n\nOutput raw valid JSON only."}
    ],
    "temperature": 0.1,
    "max_tokens": 4096,
}

client = httpx.Client(timeout=60.0)
r = client.post(endpoint, json=body, headers=headers)
print("STATUS:", r.status_code)
content = r.json()["choices"][0]["message"]["content"]
print("LENGTH:", len(content))
with open("scratch/raw_output.txt", "w", encoding="utf-8") as f:
    f.write(content)
print("Saved to scratch/raw_output.txt")

