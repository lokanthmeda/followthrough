import json
import re

def parse_target_json(text: str) -> dict:
    text = text.strip()

    # 1. Direct parse
    try:
        val = json.loads(text)
        if isinstance(val, dict):
            return val
    except Exception:
        pass

    candidates = []

    # 2. Extract from ALL markdown code fences
    for m in re.finditer(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text):
        try:
            val = json.loads(m.group(1))
            if isinstance(val, dict):
                candidates.append(val)
        except Exception:
            pass

    # 3. Widest outer braces
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            val = json.loads(text[first_brace:last_brace + 1])
            if isinstance(val, dict):
                candidates.append(val)
        except Exception:
            pass

    # 4. Scan braces from longest span to shortest
    if not candidates:
        starts = [i for i, ch in enumerate(text) if ch == '{']
        ends = [i for i, ch in enumerate(text) if ch == '}']
        for s in starts:
            for e in reversed(ends):
                if e > s and (e - s) > 30:
                    try:
                        val = json.loads(text[s:e + 1])
                        if isinstance(val, dict):
                            candidates.append(val)
                            break
                    except Exception:
                        continue

    if not candidates:
        raise ValueError(f"No JSON found in text: {text[:300]}")

    # Prioritize candidate that has target domain keys
    domain_keys = {"decisions", "action_items", "meeting", "relation", "confidence"}
    scored = []
    for c in candidates:
        score = sum(1 for k in domain_keys if k in c)
        scored.append((score, len(str(c)), c))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return scored[0][2]

# Test with schema snippet before real output
mock_output = """Here is the snippet:
```json
{"type": "product", "value": "string"}
```

And here is the final meeting extraction:
```json
{
  "meeting": {"title": "Followthrough", "started_at": null, "timezone": "Asia/Kolkata"},
  "decisions": [{"statement": "PostgreSQL database for storage", "topic": "storage"}],
  "action_items": [{"title": "Build ingestion module", "owner": "Priya", "due_date": "2026-11-05", "flags": []}],
  "open_questions": []
}
```
"""

res = parse_target_json(mock_output)
print("SUCCESSFULLY PARSED TARGET OBJECT:")
print("Keys:", list(res.keys()))
print("Decisions:", len(res.get("decisions", [])))
print("Action Items:", len(res.get("action_items", [])))

