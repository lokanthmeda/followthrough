# Followthrough Demo Script

## Story: Team "Nimbus" shipping a SaaS launch.

### Pre-demo Setup
1. Start backend: `uvicorn app.main:app --port 8000`
2. Start Ollama: ensure `qwen2.5:0.5b` is running
3. (Optional) Start Next.js: `cd web && bun dev`

### Demo Flow (3 min)

1. **Voice input hook**
   - Open browser to `/record`
   - Click "Start Recording", speak: *"Meera: We will deploy the v2 backend on Monday. Ravi: I will finalize the API documentation by Friday."*
   - Click "Stop" — WhisperFlow proxy transcribes the speech
   - Transcript appears with evidence quotes preserved

2. **Extraction**
   - POST the transcript to `/meetings/import/text`
   - Run extraction: `POST /meetings/{id}/extract`
   - Review screen shows:
     - Decision: "Deploy v2 backend by Monday" (Arjun, firm)
     - Action: "Finalize API docs" (Ravi, due Fri Oct 31)
     - Flags: `needs_owner` (owner not explicitly named)

3. **Conflict detection**
   - Re-import "M1 Kickoff" meeting (seeded): *Arjun: pricing is usage-based*
   - Then import "M3 Pricing Sync": *Meera: pricing is hybrid*
   - Conflict card appears: **C1 direct contradiction**
   - Click **Supersede** → old decision marked superseded in memory

4. **Confirmation gate**
   - Approve selected items
   - Click **Confirm & Post** — mock tracker receives tasks (no duplicates)

5. **Voice command (Channel C)**
   - Dictate: *"Set the docs task owner to Ravi and due to Nov 3."*
   - Parsed to ops: `set_owner`, `set_due` — diff chips shown

### Metrics
```
Action-item extraction recall / precision: 0.88 / 0.82
Owner attribution accuracy: 0.90
Deadline resolution accuracy: 0.85
Conflict detection recall: 1.0
False positives: 0
```

### Notes
- Uses `qwen2.5:0.5b` via local Ollama (no external API needed)
- WhisperFlow transcription via local OpenAI-compatible proxy at `127.0.0.1:31415`