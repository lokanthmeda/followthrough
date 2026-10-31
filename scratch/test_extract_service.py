import sys
sys.path.insert(0, ".")
import asyncio
from datetime import datetime, timezone
from backend.app.models import Utterance
from backend.app.services.extract import extract

utterances = [
    Utterance(seq=0, speaker_label="Lokanath", text_raw="Good morning everyone. Let's start with the product planning discussion for the Followthrough project. Our goal for this sprint is to launch the first working version by November 15th."),
    Utterance(seq=1, speaker_label="Priya", text_raw="I think the first priority should be the transcript ingestion and decision extraction module. Without that, the rest of the workflow won't work."),
    Utterance(seq=2, speaker_label="Lokanath", text_raw="Agreed. Let's make transcript ingestion the first priority. Priya, you own the transcript ingestion module. Please complete it by November 5th."),
    Utterance(seq=3, speaker_label="Priya", text_raw="Sure, I'll take ownership of that."),
    Utterance(seq=4, speaker_label="Lokanath", text_raw="Rahul, can you handle the task tracker integration?"),
    Utterance(seq=5, speaker_label="Rahul", text_raw="Yes. I'll integrate the task tracker and make sure tasks can be created automatically after confirmation. I'll complete it by November 7th."),
    Utterance(seq=6, speaker_label="Lokanath", text_raw="Good. Anita, please work on the weekly digest functionality. I want every team member to receive a summary of their open tasks every Friday."),
    Utterance(seq=7, speaker_label="Anita", text_raw="Okay. I'll complete the weekly digest by November 10th."),
    Utterance(seq=8, speaker_label="Lokanath", text_raw="One more important decision: nothing should be automatically posted to the task tracker without a human confirmation. Even if the AI extracts an action item correctly, the user must confirm it before creating the task."),
    Utterance(seq=9, speaker_label="Priya", text_raw="Understood."),
    Utterance(seq=10, speaker_label="Lokanath", text_raw="And let's use the existing PostgreSQL database for storing meeting memory and decisions."),
    Utterance(seq=11, speaker_label="Rahul", text_raw="Okay, I'll use PostgreSQL for that."),
]

async def run():
    print("Running extract service...")
    t0 = datetime.now()
    res = await extract(
        utterances=utterances,
        meeting_title="Meeting 1 — Product Planning Meeting",
        started_at=datetime.now(tz=timezone.utc),
        timezone="Asia/Kolkata",
        participants=["Lokanath", "Priya", "Rahul", "Anita"],
    )
    elapsed = (datetime.now() - t0).total_seconds()
    print(f"Extraction completed in {elapsed:.1f}s!")
    print("KEYS:", list(res.keys()))
    import pprint
    pprint.pprint(res)

asyncio.run(run())

