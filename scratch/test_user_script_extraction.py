from datetime import datetime
from backend.app.models import Utterance
from backend.app.services.ingest import build_utterances
from backend.app.services.extract import _heuristic_extract

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

print("--- TESTING M1 ---")
utts1 = build_utterances("m1", m1_text)
res1 = _heuristic_extract(utts1, "Meeting 1", datetime(2026, 10, 31), "Asia/Kolkata", ["Lokanath", "Priya", "Rahul", "Anita"])
print("M1 Decisions:", len(res1["decisions"]))
for d in res1["decisions"]:
    print(" ", d["statement"])
print("M1 Action Items:", len(res1["action_items"]))
for a in res1["action_items"]:
    print(" ", a["owner"], "->", a["title"], a["due_date"])

print("\n--- TESTING M2 ---")
utts2 = build_utterances("m2", m2_text)
res2 = _heuristic_extract(utts2, "Meeting 2", datetime(2026, 11, 2), "Asia/Kolkata", ["Lokanath", "Priya", "Rahul", "Anita"])
print("M2 Decisions:", len(res2["decisions"]))
for d in res2["decisions"]:
    print(" ", d["statement"])
print("M2 Action Items:", len(res2["action_items"]))
for a in res2["action_items"]:
    print(" ", a["owner"], "->", a["title"], a["due_date"])

