"""Background scheduler for reminders and weekly digests."""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..db import AsyncSessionLocal
from ..services.reminders import process_due_reminders
from ..services.digest import send_weekly_digests

log = logging.getLogger("followthrough.scheduler")
scheduler = AsyncIOScheduler()


async def run_reminders():
    log.info("Checking reminders...")
    async with AsyncSessionLocal() as db:
        result = await process_due_reminders(db)
        log.info("Reminders result: %s", result)
        print(f"[scheduler] reminders: {result}")


async def run_digests():
    log.info("Generating weekly digests...")
    async with AsyncSessionLocal() as db:
        result = await send_weekly_digests(db)
        log.info("Digests result: %s", result)
        print(f"[scheduler] digests: {result}")


def start_scheduler():
    if scheduler.running:
        return
    scheduler.add_job(run_reminders, "interval", minutes=15, id="reminders", replace_existing=True)
    scheduler.add_job(run_digests, "cron", day_of_week="mon", hour=9, id="digests", replace_existing=True)
    scheduler.start()
    log.info("Scheduler started (reminders every 15m, digests Mon 09:00)")
