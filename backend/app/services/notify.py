"""Outbound notifications: Slack webhook and/or console (demo-safe)."""
import json
import logging
from typing import Any

import httpx

from ..config import settings

log = logging.getLogger("followthrough.notify")


async def send_notification(
    subject: str,
    body: str,
    *,
    recipient: str | None = None,
    channel: str = "console",
    payload: dict[str, Any] | None = None,
) -> dict:
    """Deliver a notification. Always logs; optionally posts to Slack."""
    record = {
        "channel": channel,
        "recipient": recipient,
        "subject": subject,
        "body": body,
        "payload": payload or {},
        "delivered": False,
    }

    log.info("NOTIFY [%s] to=%s | %s | %s", channel, recipient, subject, body)
    try:
        print(f"[NOTIFY/{channel}] to={recipient} | {subject}\n{body}")
    except UnicodeEncodeError:
        safe = f"[NOTIFY/{channel}] to={recipient} | {subject}\n{body}".encode("ascii", "replace").decode("ascii")
        print(safe)

    if settings.slack_webhook_url:
        try:
            text = f"*{subject}*\n{body}"
            if recipient:
                text = f"To: {recipient}\n{text}"
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(settings.slack_webhook_url, json={"text": text})
                record["delivered"] = r.is_success
                record["channel"] = "slack"
        except Exception as e:
            log.warning("Slack notify failed: %s", e)
            record["error"] = str(e)
    else:
        # Demo mode: treat console delivery as success
        record["delivered"] = True
        record["channel"] = "console"

    return record
