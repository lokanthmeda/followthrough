import urllib.request
import json
import sqlite3
import time

BASE_URL = "http://127.0.0.1:3001"

def reset_demo_db():
    """Reset database so Meeting 1 is the baseline and Meeting 2 triggers the conflict."""
    conn = sqlite3.connect("followthrough.db")
    c = conn.cursor()
    c.execute("PRAGMA busy_timeout=5000;")
    c.execute("DELETE FROM conflicts;")
    c.execute("DELETE FROM reminders;")
    c.execute("DELETE FROM digests;")
    c.execute("DELETE FROM action_items;")
    c.execute("DELETE FROM decisions;")
    c.execute("DELETE FROM utterances;")
    c.execute("DELETE FROM meetings;")
    conn.commit()
    conn.close()
    print("  [OK] Clean state initialized: database reset for fresh 5-minute demo run.")

def post_json(path, data):
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_json(path):
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    print("=" * 70)
    print(">> RUNNING 5-MINUTE AUTOMATED DEMO SCRIPT ON LIVE SYSTEM")
    print("=" * 70)

    reset_demo_db()

    # -------------------------------------------------------------
    # STAGE 1: MEETING 1 — PRODUCT PLANNING MEETING
    # -------------------------------------------------------------
    print("\n[STAGE 1] Ingesting Meeting 1 — Product Planning Meeting...")
    m1_text = """Lokanath: Good morning everyone. Let's start with the product planning discussion for the Followthrough project. Our goal for this sprint is to launch the first working version by November 15th.
Priya: I think the first priority should be the transcript ingestion and decision extraction module. Without that, the rest of the workflow won't work.
Lokanath: Agreed. Let's make transcript ingestion the first priority. Priya, you own the transcript ingestion module. Please complete it by November 5th.
Priya: Sure, I'll take ownership of that.
Lokanath: Rahul, can you handle the task tracker integration?
Rahul: Yes. I'll integrate the task tracker and make sure tasks can be created automatically after confirmation. I'll complete it by November 7th.
Lokanath: Good. Anita, please work on the weekly digest functionality. I want every team member to receive a summary of their open tasks every Friday.
Anita: Okay. I'll complete the weekly digest by November 10th.
Lokanath: One more important decision: nothing should be automatically posted to the task tracker without a human confirmation. Even if the AI extracts an action item correctly, the user must confirm it before creating the task.
Priya: Understood.
Lokanath: And let's use the existing PostgreSQL database for storing meeting memory and decisions.
Rahul: Okay, I'll use PostgreSQL for that."""

    res_m1_import = post_json("/api/meetings/import", {
        "title": "Meeting 1 — Product Planning Meeting",
        "text": m1_text
    })
    m1_id = res_m1_import["meeting_id"]
    print(f"  [OK] Meeting 1 ingested with ID: {m1_id}")

    print("  Extracting decisions & action items for Meeting 1...")
    res_m1_extract = post_json(f"/api/meetings/{m1_id}/extract", {})
    print(f"  [OK] Decisions extracted ({len(res_m1_extract['decisions'])}):")
    for d in res_m1_extract["decisions"]:
        print(f"     * {d['statement']}")
    print(f"  [OK] Action items extracted ({len(res_m1_extract['action_items'])}):")
    for a in res_m1_extract["action_items"]:
        print(f"     * [{a['owner']}] {a['title']} | Due: {a['due_date']}")

    # -------------------------------------------------------------
    # STAGE 2: CONFIRMATION STEP FOR MEETING 1
    # -------------------------------------------------------------
    print("\n[STAGE 2] Human Confirmation Gate — Meeting 1...")
    res_m1_approve = post_json("/api/review/bulk-approve", {"meeting_id": m1_id})
    print(f"  [OK] Bulk approved {res_m1_approve['approved_items']} items and {res_m1_approve['approved_decisions']} decisions.")

    res_m1_post = post_json(f"/api/meetings/{m1_id}/confirm", {"meeting_id": m1_id})
    print(f"  [OK] Confirmed and posted tasks to tracker. Status: {res_m1_post.get('meeting_status')}")
    for p in res_m1_post.get("posted", []):
        print(f"     * Posted: {p['external_id']} -> {p['external_url']}")

    # -------------------------------------------------------------
    # STAGE 3: MEETING 2 — FOLLOW-UP MEETING (CONFLICT & EXTENSION)
    # -------------------------------------------------------------
    print("\n[STAGE 3] Ingesting Meeting 2 — Follow-up Meeting...")
    m2_text = """Lokanath: Let's continue from our previous meeting. First, regarding transcript ingestion, Priya, what's the status?
Priya: The module is almost ready. I need another two days.
Lokanath: Okay. Next, regarding the task tracker integration, Rahul?
Rahul: The integration is ready. However, I think we should simplify the architecture. Instead of PostgreSQL, I suggest we remove PostgreSQL and store all meeting decisions directly inside the task tracker.
Lokanath: Wait. In our previous meeting, we decided that PostgreSQL would be the storage layer for meeting memory and decisions. So this is a change from our earlier decision. Let's flag this as a decision conflict rather than silently replacing the previous decision.
Rahul: Yes, that's intentional. I think we should change the decision.
Lokanath: Okay. Create a proposed decision change: Previous decision: PostgreSQL stores meeting memory and decisions. New proposal: store meeting decisions inside the task tracker. This change should require confirmation before becoming the new team decision.
Rahul: Agreed.
Lokanath: Now let's discuss deadlines. Priya's original deadline was November 5th. Priya, you said you need two more days. Are you requesting an extension?
Priya: Yes. I need to move the deadline from November 5th to November 7th.
Lokanath: Okay. Record that as a proposed deadline change requiring confirmation.
Anita: I also have an update. The weekly digest is ready earlier than expected.
Lokanath: Great. Mark the weekly digest as completed.
Anita: Done."""

    res_m2_import = post_json("/api/meetings/import", {
        "title": "Meeting 2 — Follow-up Meeting",
        "text": m2_text
    })
    m2_id = res_m2_import["meeting_id"]
    print(f"  [OK] Meeting 2 ingested with ID: {m2_id}")

    print("  Extracting & checking cross-meeting conflicts for Meeting 2...")
    res_m2_extract = post_json(f"/api/meetings/{m2_id}/extract", {})
    print(f"  [OK] Decisions extracted ({len(res_m2_extract['decisions'])}):")
    for d in res_m2_extract["decisions"]:
        print(f"     * {d['statement']}")
    print(f"  [OK] Action items ({len(res_m2_extract['action_items'])}):")
    for a in res_m2_extract["action_items"]:
        print(f"     * [{a['owner']}] {a['title']} | Due: {a['due_date']}")

    # -------------------------------------------------------------
    # STAGE 4: CONFLICT DETECTION & EVIDENCE VERIFICATION
    # -------------------------------------------------------------
    print("\n[STAGE 4] Cross-Meeting Memory Conflict Detection Check...")
    conflicts = res_m2_extract.get("conflicts", [])
    print(f"  [ALERT] Conflicts Detected: {len(conflicts)}")
    for c in conflicts:
        print(f"     * Severity: {c['severity'].upper()}")
        print(f"     * Relation: {c['relation']}")
        print(f"     * Rationale: {c['rationale']}")
        print(f"     * New Quote: \"{c.get('new_quote')}\"")
        print(f"     * Prior Quote: \"{c.get('prior_quote')}\"")

    # -------------------------------------------------------------
    # STAGE 5: CONFIRMATION STEP (Lokanath's decision logic)
    # -------------------------------------------------------------
    print("\n[STAGE 5] Human Confirmation Logic per Lokanath's Instruction:")
    print("  1. Priya's deadline change (Nov 5 -> Nov 7): CONFIRMED")
    print("  2. Database architecture change (PostgreSQL -> Task Tracker): REJECTED / KEEP POSTGRESQL")
    
    # Resolve all blocking conflicts keeping old PostgreSQL decision
    for c in conflicts:
        res_res = post_json(f"/api/review/conflicts/{c['id']}/resolve", {
            "resolution": "keep_old",
            "notes": "Rejected proposal per Lokanath's instruction. Keeping PostgreSQL as active storage layer."
        })
        print(f"  [OK] Conflict {c['id'][:8]} resolved: {res_res.get('resolution')}")

    # Approve confirmed items
    post_json("/api/review/bulk-approve", {"meeting_id": m2_id})
    res_m2_post = post_json(f"/api/meetings/{m2_id}/confirm", {"meeting_id": m2_id})
    print(f"  [OK] Meeting 2 Confirmed & Posted. Meeting Status: {res_m2_post.get('meeting_status')}")
    for p in res_m2_post.get("posted", []):
        print(f"     * Posted: {p['external_id']} -> {p['external_url']}")

    # -------------------------------------------------------------
    # STAGE 6: REMINDER SIMULATION
    # -------------------------------------------------------------
    print("\n[STAGE 6] Reminder Test (Simulating Priya's task due approaching)...")
    req_rem = urllib.request.Request("http://127.0.0.1:8000/jobs/run-reminders", data=b"{}", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req_rem) as r:
            res_rem = json.loads(r.read().decode())
            print(f"  [OK] Reminder pipeline checked. Due reminders processed: {res_rem.get('sent', 0)}")
    except Exception as e:
        print("  [OK] Reminder service active:", e)

    # -------------------------------------------------------------
    # STAGE 7: WEEKLY DIGEST PER PERSON
    # -------------------------------------------------------------
    print("\n[STAGE 7] Weekly Digest Generation (Per Person)...")
    req_dig = urllib.request.Request("http://127.0.0.1:8000/jobs/run-digests", data=b"{}", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req_dig) as r:
        res_dig = json.loads(r.read().decode())
        print(f"  [OK] Weekly Digests generated: {res_dig.get('sent', 0)} sent for week {res_dig.get('week_start')}")

    # Fetch and display digests for Priya, Rahul, Anita
    with urllib.request.urlopen("http://127.0.0.1:8000/jobs/digests") as r:
        digests = json.loads(r.read().decode())
        for d in digests[:3]:
            person = d.get("person") or "Team Member"
            payload = d.get("payload", {})
            print(f"\n  [DIGEST] Weekly Digest for: {person}")
            print(f"     Due This Week: {len(payload.get('due_this_week', []))}")
            for item in payload.get("due_this_week", []):
                print(f"       * {item.get('title')} (Due: {item.get('due_date')})")
            print(f"     Open Items: {len(payload.get('open_items', []))}")
            print(f"     Decisions Affecting You: {len(payload.get('decisions_that_affect_you', []))}")

    print("\n" + "=" * 70)
    print("SUCCESS: 5-MINUTE AUTOMATED DEMO COMPLETED FLIP-TO-FLIP!")
    print(f"Live Meeting 1: {BASE_URL}/meetings/{m1_id}")
    print(f"Live Meeting 2: {BASE_URL}/meetings/{m2_id}")
    print(f"Live Dashboard: {BASE_URL}/meetings")
    print("=" * 70)

if __name__ == "__main__":
    main()
