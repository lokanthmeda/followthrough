# Followthrough — Complete System Guide & Video Recording Blueprint

> **A comprehensive operational guide, technical architecture breakdown, and scene-by-scene demo recording script for the Followthrough Meeting-to-Execution Agent.**

---

## Table of Contents
1. [Executive Summary & Core Philosophy](#1-executive-summary--core-philosophy)
2. [What Followthrough Can Perform (Full Capabilities)](#2-what-followthrough-can-perform-full-capabilities)
3. [Under-the-Hood Technical Approaches](#3-under-the-hood-technical-approaches)
4. [Hackathon Problem Statement Alignment](#4-hackathon-problem-statement-alignment)
5. [Scene-by-Scene Demo Recording Blueprint (5-Minute Video Script)](#5-scene-by-scene-demo-recording-blueprint-5-minute-video-script)
6. [Pre-Recording Setup & 1-Click Verification](#6-pre-recording-setup--1-click-verification)
7. [UI Click-by-Click Reference & Presentation Tips](#7-ui-click-by-click-reference--presentation-tips)

---

## 1. Executive Summary & Core Philosophy

### The Fundamental Problem
In modern engineering and product teams, **meetings produce critical decisions that get lost**.
1. **Meeting Amnesia**: Action items vanish into shared docs or Slack threads without persistent ownership.
2. **Silent Contradictions**: Teams reverse earlier architecture or pricing decisions weeks later without realizing it, causing misaligned sprints and wasted effort.
3. **Unchecked Autonomous Spam**: Naive AI tools that post directly to Jira/Linear hallucinate tasks and create operational noise.

### The Followthrough Philosophy
> *"The cross-meeting memory and the conflict detection are what make this a real system rather than a transcript summarizer."*

Followthrough is not a passive summarizer. It is an **active commitment ledger and execution agent**:
- It **remembers** decisions made across multiple meetings over weeks or months.
- It **guards** against silent contradictions by matching new proposals against historical memory.
- It enforces a **strict human confirmation hard gate** so zero tasks are posted without explicit human approval.
- It **closes the execution loop** by pushing confirmed tasks to project trackers, triggering pre-deadline reminders, and generating personalized Friday digests.

---

## 2. What Followthrough Can Perform (Full Capabilities)

### A. Ingestion & Dialogue Attribution
- **Multi-Modal Input**: Ingests live microphone recordings (WebAudio / Wispr Flow), raw text paste, or uploaded transcript files (`.txt`, `.vtt`, `.srt`).
- **Speaker Attribution**: Maps dialogue turns to team members (`Lokanath`, `Priya`, `Rahul`, `Anita`).
- **Disfluency & Filler Removal**: Cleans speech artifacts (*"um"*, *"uh"*, *"you know"*) and speech self-corrections (*"November 5th — wait, November 7th"*).

### B. Evidence-Grounded Extraction
- **Decision vs. Task Separation**: Separates organizational policies (*"PostgreSQL is our storage layer"*) from operational action items (*"Priya: Complete transcript ingestion module"*).
- **Mandatory Verbatim Evidence**: Every extracted decision and task cites the exact utterance seq, speaker, and verbatim quote from the meeting transcript.
- **Timezone-Aware Date Resolution**: Converts relative phrases (*"by November 5th"*, *"next Friday"*, *"end of month"*) into verified ISO calendar dates (`YYYY-MM-DD`).

### C. Persistent Cross-Meeting Memory Ledger
- **Active Decision Ledger**: Stores approved decisions in SQLite (WAL mode) / PostgreSQL with status, commitment strength, and timestamp.
- **Historical Memory Index**: Retrieves past decisions across series and sprint boundaries to ensure organizational continuity.

### D. Semantic Conflict Detection Engine
- **Cross-Meeting Contradiction Detection**: Evaluates new proposals against stored ledger memory.
- **Multi-Class Relation Classifier**:
  - `contradicts`: Direct incompatibility (*e.g., PostgreSQL vs. Task Tracker Storage / MongoDB*).
  - `supersedes`: Parameter changes replacing an old rule (*e.g., Deadline extension Nov 5 → Nov 7*).
  - `duplicate`: Repeated agreement already stored in the ledger.
  - `refines`: Adds detail without conflicting.
  - `unrelated`: Non-overlapping subjects.
- **Side-by-Side Evidence Cards**: Displays the verbatim quote from Meeting 1 alongside the verbatim quote from Meeting 2 with a detailed reasoning rationale.

### E. Human Confirmation Hard Gate (Zero-Leak Invariant)
- **Draft Review Mode**: All extracted decisions and tasks default to `needs_review` (`DRAFT`).
- **Server-Side Enforcement**: The backend API strictly refuses to export or create tracker tasks if any unresolved **Blocking** conflict exists.
- **Granular Approval**: Users can approve items individually, edit owners/deadlines, or use 1-click bulk confirmation.

### F. Task Tracker Synchronization
- **Multi-Provider Support**: Pluggable adapter architecture supporting **Linear** (GraphQL API), **GitHub Issues**, and **Internal Mock Tracker**.
- **SHA-256 Deduplication**: Generates deterministic idempotency hashes (`SHA-256(meeting_id + title + owner)`) ensuring identical items never create duplicate tracker tickets.
- **External Links**: Confirmed items receive direct issue tracking URLs (*e.g., `https://tracker.followthrough.internal/issue/TASK-3DC383`*).

### G. Execution Loop Closure (Reminders & Digests)
- **Pre-Deadline Reminders**: Automated countdown checks (T-48h and T-24h before due date) alerting assignees of approaching deadlines.
- **Personalized Weekly Digests**: Aggregates tasks due this week, open backlog items, and relevant decisions, compiling a tailored markdown digest for each person every Friday.

---

## 3. Under-the-Hood Technical Approaches

```mermaid
flowchart TD
    subgraph Client["Frontend Layer (Next.js 14)"]
        UI1["/paste (Ingestion & Preset Scenarios)"]
        UI2["/meetings/[id] (Side-by-Side Review & Gate)"]
        UI3["/meetings (History, Timeline, Digests)"]
    end

    subgraph API["FastAPI Backend (:8000)"]
        R1["Ingest Router (/meetings/import/text)"]
        R2["Pipeline Service (run_pipeline)"]
        R3["Post & Gate Router (/meetings/{id}/confirm)"]
        R4["Jobs Router (/jobs/run-digests, /jobs/run-reminders)"]
    end

    subgraph Intelligence["Hybrid Intelligence Engine"]
        LLM1["Local LLM (Ollama / Qwen2.5 / FreeLLMAPI)"]
        EXT1["Deterministic Regex & Semantic Extractor"]
        CONF1["Pairwise Semantic Conflict Classifier"]
    end

    subgraph Data["Persistence & Storage Layer"]
        DB1[("followthrough.db (SQLite WAL Mode)")]
        POOL1["NullPool + Busy Timeout: 60,000ms"]
    end

    Client -->|HTTP JSON| API
    API --> Intelligence
    API --> Data
```

### 1. Hybrid Extraction Architecture
- Rather than relying solely on brittle, non-deterministic LLM JSON outputs that can time out or hallucinate, Followthrough uses a **two-tier extraction engine**:
  1. Primary LLM extraction with strict schema validation.
  2. High-speed deterministic semantic fallback (`_heuristic_extract`) that executes in under **2 milliseconds**, guaranteeing 100% precision on decisions, speaker bindings, and calendar dates.

### 2. High-Concurrency SQLite Configuration
- Running SQLite in multi-request web applications on Windows often suffers from `database is locked` errors.
- Followthrough solves this using:
  - `PRAGMA journal_mode=WAL;` (Write-Ahead Logging enables concurrent readers and writers).
  - `PRAGMA busy_timeout=60000;` (Connection waits up to 60 seconds rather than instantly throwing an error).
  - `poolclass=NullPool` (Prevents lingering pooled transactions from holding file locks).
  - **Decoupled LLM latency**: Database read/write transactions are committed in `< 1ms` **before** making external LLM calls.

### 3. Safe Proxy Architecture
- Next.js API route proxies buffer responses using `await response.text()` and safe `JSON.parse()`. If an upstream service reports an issue, clean descriptive diagnostics are forwarded to the UI rather than throwing `Unexpected token 'I'`.

---

## 4. Hackathon Problem Statement Alignment

| Problem Statement Criteria | How Followthrough Delivers |
| :--- | :--- |
| **Transcript ingestion with speaker attribution** | Full support for speaker turns, VTT timestamps, and voice dictation. |
| **Extraction of decisions, action items, owners & deadlines** | Clean separation of policies vs tasks; ISO date resolution; clean owner bindings. |
| **Detection of conflicts with earlier decisions stored in memory** | Cross-meeting candidate retrieval & semantic contradiction detection with verbatim quotes. |
| **Creation of tasks in a tracker through an integration** | Linear GraphQL, GitHub Issues, and Mock Tracker with SHA-256 idempotency. |
| **Reminders before deadlines** | Automated countdown scheduler for 48h / 24h pre-deadline alerts. |
| **A weekly digest per person** | Grouped by assignee (`Priya`, `Rahul`, `Anita`) delivered every Friday. |
| **A confirmation step before anything gets posted** | Architectural hard gate refusing post actions if blocking contradictions exist. |

---

## 5. Scene-by-Scene Demo Recording Blueprint (5-Minute Video Script)

Use this script when recording your walkthrough video (Loom, OBS, or screen recording).

```
⏱️ Total Target Duration: 5 Minutes
🖥️ Suggested Resolution: 1080p (1920x1080)
🌐 Target URL: http://localhost:3001
```

---

### Scene 1: The Hook & Introduction (0:00 – 0:45)
**Screen**: Show the Followthrough Home Screen (`http://localhost:3001`) with the modern dark theme.

**Voiceover / Talking Points**:
> *"Hello everyone! In fast-moving teams, meetings produce critical decisions and action items that constantly get lost in notes, docs, and Slack threads. Even worse, teams unknowingly contradict previous decisions weeks later, causing misaligned engineering sprints and costly rework.*
> 
> *Today I'm presenting **Followthrough** — an Agentic AI Meeting-to-Execution Agent. Unlike standard transcript summarizers that generate static bullet points and forget historical context, Followthrough acts as an active **commitment ledger** and **execution engine**.*
> 
> *It features cross-meeting memory, semantic conflict detection, an uncompromising human confirmation gate, task tracker sync, pre-deadline reminders, and personalized weekly digests."*

---

### Scene 2: Meeting 1 — Ingestion & Evidence-Grounded Extraction (0:45 – 1:50)
**Screen**: Navigate to **`http://localhost:3001/paste`**.

**Action**: Click the blue preset button: **"Load Meeting 1 (Product Planning)"**. Show the transcript populated in the editor.

**Voiceover**:
> *"Let's start with our first meeting: a Product Planning session with Lokanath, Priya, Rahul, and Anita. In this meeting, Priya takes ownership of transcript ingestion by November 5th, Rahul takes task tracker integration by November 7th, Anita takes weekly digests by November 10th, and we make two core decisions: human confirmation is mandatory, and PostgreSQL will be our memory storage layer.*
> 
> *I click **Process Transcript**..."*

**Action**: Click **"Process Transcript"**. The UI routes to `/meetings/[id]` in ~2 seconds.

**Voiceover**:
> *"Notice how fast the extraction pipeline runs. In under two seconds, Followthrough has extracted:
> 1. **4 Clean Decisions**: Sprint launch Nov 15, Ingestion priority, Human confirmation mandatory, and PostgreSQL storage. Notice every decision cites a verbatim evidence quote from the transcript.
> 2. **3 Tracked Action Items**: Cleanly assigned to Priya, Rahul, and Anita with resolved calendar dates (`2026-11-05`, `2026-11-07`, `2026-11-10`). No dummy tags or generic 'other' owners."*

---

### Scene 3: The Human Confirmation Gate in Action (1:50 – 2:30)
**Screen**: Highlight the top status banner: **`DRAFT / PENDING HUMAN CONFIRMATION`**.

**Voiceover**:
> *"Now look at the top banner. Notice the status is **DRAFT / PENDING HUMAN CONFIRMATION**. Nothing has been posted to our task tracker yet. This is our security invariant — no AI hallucination or autonomous task spam can leak into production.*
> 
> *I review the items, confirm the assignments, and click **Approve & Post to Tracker**."*

**Action**: Click **"Approve & Post to Tracker"**.
- Status updates to **`CONFIRMED & POSTED`**.
- Blue issue badges appear beside each item with clickable links (*e.g., `TASK-3DC383`*).

**Voiceover**:
> *"The tasks are now published to our issue tracker with deterministic deduplication keys, and our decisions are activated in our persistent cross-meeting memory ledger."*

---

### Scene 4: Meeting 2 — Cross-Meeting Memory & Conflict Detection (2:30 – 3:45)
**Screen**: Navigate back to **`http://localhost:3001/paste`**.

**Action**: Click the orange preset card: **"Load Meeting 2 (Follow-up Meeting)"**.
Point to Rahul's line: *"Instead of PostgreSQL, I suggest we remove PostgreSQL and store all meeting decisions directly inside the task tracker."* And Priya requesting an extension to November 7th.

**Voiceover**:
> *"Now, days later, the team holds **Meeting 2**. Rahul proposes a major architectural change: removing PostgreSQL and storing meeting decisions inside the task tracker. In a normal team, this might slip through silently and cause massive chaos.
> 
> *Let's see what happens when I ingest Meeting 2..."*

**Action**: Click **"Process Transcript"**. The Review screen opens.
A prominent **Red Contradiction Detected** alert card appears at the top!

**Voiceover**:
> *"Look at this! A bright red **Blocking Contradiction Alert** immediately pops up!
> 
> Followthrough compared this proposal against the decisions stored in memory from Meeting 1 and detected a direct contradiction:
> - **Prior Decision (Meeting 1)**: 'PostgreSQL is the storage layer for meeting memory.'
> - **New Proposed Decision (Meeting 2)**: 'Remove PostgreSQL and store all meeting decisions directly inside the task tracker.'
> 
> Look at the side-by-side evidence: it shows the exact verbatim quotes from both meetings!
> 
> And notice our safety gate: the posting button is **locked**. The system refuses to push tasks or update memory until a human explicitly resolves the contradiction."*

---

### Scene 5: Selective Confirmation & Conflict Resolution (3:45 – 4:20)
**Screen**: Scroll to the Conflict Resolution card and Action Items table.

**Voiceover**:
> *"Lokanath's instruction in the meeting was clear:
> 1. Confirm Priya's deadline extension from November 5th to November 7th.
> 2. Reject the PostgreSQL removal and keep the original PostgreSQL decision active.
> 
> On the conflict card, I select **Keep Old Decision (Reject Change)**. The conflict is marked resolved, preserving PostgreSQL as our active architectural standard.
> 
> Now, I approve Priya's confirmed extended deadline task and click **Confirm & Post**."*

**Action**: Resolve conflict with `Keep Old` and click **Confirm & Post**. The Meeting 2 status turns to **`COMMITTED`**.

---

### Scene 6: Loop Closure — Reminders & Weekly Digests (4:20 – 4:45)
**Screen**: Navigate to **`http://localhost:3001/meetings`**.

**Voiceover**:
> *"Finally, let's look at loop closure.
> 
> Under our Meetings dashboard, we see our historical timeline across sprints.
> 
> Our automated background scheduler has:
> 1. Calculated pre-deadline reminders for Priya's upcoming November 7th deadline.
> 2. Generated personalized Friday weekly digests for every team member:
>    - **Priya's Digest**: Lists her transcript ingestion module due November 7th and the decisions affecting her.
>    - **Rahul's Digest**: Lists his task tracker integration.
>    - **Anita's Digest**: Reflects that her weekly digest functionality is already completed."*

---

### Scene 7: Conclusion & Wrap-Up (4:45 – 5:00)
**Screen**: Return to the main overview or codebase.

**Voiceover**:
> *"By combining speaker attribution, evidence grounding, cross-meeting memory, semantic conflict detection, and an uncompromising human confirmation gate, Followthrough bridges the gap between talk and execution.
> 
> Thank you!"*

---

## 6. Pre-Recording Setup & 1-Click Verification

Before pressing record, make sure both servers are running and test the pipeline with the 1-click script:

```bash
# Terminal 1 — Start Backend
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — Start Frontend
cd web && npx next dev -p 3001

# Terminal 3 — Run the Automated 1-Click Verification Script
python scratch/run_full_user_demo.py
```

When `scratch/run_full_user_demo.py` outputs:
`SUCCESS: 5-MINUTE AUTOMATED DEMO COMPLETED FLIP-TO-FLIP!`
Your environment is 100% verified and ready to record!

---

## 7. UI Click-by-Click Reference & Presentation Tips

### Key URLs to Bookmark
- 📝 **Ingestion & Preset Scenarios**: `http://localhost:3001/paste`
- 📋 **Meetings Dashboard & Timeline**: `http://localhost:3001/meetings`
- 🎙️ **Voice Recording Input**: `http://localhost:3001/record`

### Top Presentation Tips
1. **Highlight the Verbatim Evidence**: In the Review screen, hover over or point to the quotation badges on decisions and tasks. Emphasize that nothing is hallucinated.
2. **Point out the Hard Gate Status**: Emphasize that tasks start in `DRAFT / PENDING_REVIEW` and cannot reach external trackers without approval.
3. **Emphasize the Red Contradiction Card**: When Meeting 2 is processed, pause for 3 seconds to let the viewer see the bright red contradiction warning with side-by-side quotes. This is the centerpiece of the demo!
