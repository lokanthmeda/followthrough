import json
import re

def parse_robust_json(text: str) -> dict:
    text = text.strip()
    # 1. Direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2. Extract from markdown code fence ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # 3. Scan from each '{' to each '}'
    start_indices = [i for i, ch in enumerate(text) if ch == '{']
    end_indices = [i for i, ch in enumerate(text) if ch == '}']
    for start in start_indices:
        for end in reversed(end_indices):
            if end > start:
                try:
                    return json.loads(text[start:end + 1])
                except Exception:
                    continue

    raise ValueError(f"Could not parse valid JSON from text: {text[:200]}")

# Test with thinking preamble
test_text = """The user wants me to extract decisions and action items from a meeting transcript.
Let's analyze the transcript and extract the relevant information.

**Meeting Context:**
- Date/Time: 2026-10-31T15:17:37 (Asia/Kolkata)

```json
{
  "meeting": {"title": "Followthrough", "started_at": null, "timezone": "Asia/Kolkata"},
  "decisions": [{"statement": "Database choice is PostgreSQL"}],
  "action_items": []
}
```
Done!"""

result = parse_robust_json(test_text)
print("SUCCESSFULLY PARSED:", result)

