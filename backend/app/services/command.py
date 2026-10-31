"""Voice command parser (PRD §6.4.4 / Appendix D)."""
from ..llm import chat_json
from ..config import settings

COMMAND_PROMPT = """Convert the user's dictated instruction into edit operations over the review queue.
The queue (ordered) is: {items_with_numbers}. Open conflicts: {conflicts}.
Dictation may include fillers and self-corrections; apply the final intent.
Allowed ops: set_owner, set_due, set_title, approve, reject, approve_all_except,
resolve_conflict(supersede|keep_old|keep_both|defer).
If a reference is ambiguous, return {{"clarify": "question to ask"}} instead of guessing.
Never approve a flagged item or resolve a conflict unless the user explicitly said so.
Output JSON only: {{"ops": [...]}}"""

async def parse_command(diction: str, items: list, conflicts: list) -> dict:
    user = COMMAND_PROMPT.format(
        items_with_numbers="\n".join(f"{i}: {it['title']}" for i, it in enumerate(items)),
        conflicts="\n".join(f"{i}: {c.get('rationale', '')}" for i, c in enumerate(conflicts)),
    ) + f"\n\nDICTATION: {diction}"
    return await chat_json(
        system="You parse voice commands into structured edit operations. Output only JSON.",
        user=user,
        model=settings.llm_model_fast,
    )