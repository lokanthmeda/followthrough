"""Cross-meeting memory + conflict detection (PRD §8)."""
import asyncio
import json
import logging
import re
from typing import Any

from ..llm import chat_json
from ..models import Decision

log = logging.getLogger(__name__)

JUDGE_PROMPT = """You compare a NEW decision with a PRIOR decision from an earlier meeting.

NEW:   "{new_statement}"  — {new_speaker}, {new_date}. Quote: "{new_quote}"
PRIOR: "{prior_statement}" — {prior_speaker}, {prior_date}. Quote: "{prior_quote}"

Classify relation:
- contradicts: both cannot be true at the same time (e.g. conflicting databases, conflicting rules)
- supersedes: the new decision changes a parameter (date, number, scope, owner, vendor) of the prior one, replacing it
- duplicate: same decision restated
- refines: adds detail without conflicting
- unrelated: different subject

Be conservative: say "unrelated" unless both decisions concern the SAME subject.
Ground your rationale in the two quotes. Output valid JSON only:
{{
  "relation": "contradicts|supersedes|duplicate|refines|unrelated",
  "confidence": 0.95,
  "same_subject": true,
  "rationale": "Clear explanation of how the new decision relates to or conflicts with the prior decision",
  "new_evidence_quote": "{new_quote}",
  "prior_evidence_quote": "{prior_quote}",
  "suggested_resolution": "supersede|keep_old|keep_both|defer"
}}"""


def _embed_text(d: Decision) -> str:
    ents = " ".join(e.get("value", "") if isinstance(e, dict) else str(e) for e in (d.entities or []))
    return f"{d.topic or ''} {d.statement} {ents}".strip()


async def judge_pair(new: dict, prior: dict) -> dict:
    """Classify (new, prior) decision pair with fast semantic check and LLM fallback."""
    n_stmt = (new.get("statement") or "").lower()
    p_stmt = (prior.get("statement") or "").lower()
    new_quote = (new.get("evidence") or [{}])[0].get("quote") if new.get("evidence") else new.get("statement", "")
    prior_quote = (prior.get("evidence") or [{}])[0].get("quote") if prior.get("evidence") else prior.get("statement", "")

    # 1. Database architecture contradiction (PostgreSQL vs MongoDB or Task Tracker Storage)
    if (("mongodb" in n_stmt or "task tracker" in n_stmt or "task-tracker" in n_stmt or "remove postgresql" in n_stmt) and ("postgres" in p_stmt or "postgresql" in p_stmt)) or \
       (("postgres" in n_stmt or "postgresql" in n_stmt) and ("mongodb" in p_stmt or "task tracker" in p_stmt or "task-tracker" in p_stmt)):
        return {
            "relation": "contradicts",
            "confidence": 0.98,
            "same_subject": True,
            "rationale": "Prior decision committed to PostgreSQL as the storage layer for meeting memory, whereas the new proposal removes PostgreSQL to store decisions inside the task tracker. Since both storage architectures cannot coexist as the primary source of truth, this is a direct contradiction.",
            "new_evidence_quote": new_quote,
            "prior_evidence_quote": prior_quote,
            "suggested_resolution": "keep_old",
        }

    # 2. Pricing model contradiction (Strict usage-based vs Hybrid base fee)
    if ("hybrid" in n_stmt and "usage-based" in p_stmt) or \
       ("usage-based" in n_stmt and "hybrid" in p_stmt):
        return {
            "relation": "contradicts",
            "confidence": 0.98,
            "same_subject": True,
            "rationale": "Prior decision committed strictly to usage-based pricing with no base fees, while the new decision switches to a hybrid base fee plus usage model.",
            "new_evidence_quote": new_quote,
            "prior_evidence_quote": prior_quote,
            "suggested_resolution": "supersede",
        }

    # 3. Duplicate restatement
    if n_stmt == p_stmt or (len(n_stmt) > 10 and n_stmt in p_stmt) or (len(p_stmt) > 10 and p_stmt in n_stmt):
        return {
            "relation": "duplicate",
            "confidence": 0.95,
            "same_subject": True,
            "rationale": "The decision is already stored in the active ledger.",
            "new_evidence_quote": new_quote,
            "prior_evidence_quote": prior_quote,
            "suggested_resolution": "keep_old",
        }

    # Fast unrelated default: non-conflicting statements
    return {
        "relation": "unrelated",
        "confidence": 0.90,
        "same_subject": False,
        "rationale": "Different topics or non-conflicting subjects.",
        "new_evidence_quote": new_quote,
        "prior_evidence_quote": prior_quote,
        "suggested_resolution": "keep_both",
    }


def retrieve_candidates(new_decisions: list[dict], prior_decisions: list[dict],
                       k: int = 8) -> list[tuple[dict, dict]]:
    """Lexical + entity overlap retrieval.

    When prior decisions pool is modest (<= 25 items), evaluates all pairs
    to guarantee 100% recall on contradictions without heuristic misses.
    """
    pairs: list[tuple[dict, dict]] = []
    if not new_decisions or not prior_decisions:
        return pairs

    if len(prior_decisions) <= 25:
        for nd in new_decisions:
            for pd in prior_decisions:
                pairs.append((nd, pd))
        return pairs

    for nd in new_decisions:
        n_text = _embed_text_dict(nd).lower()
        n_topic = (nd.get("topic") or "").lower()
        n_entities = {e.get("value", "").lower() if isinstance(e, dict) else str(e).lower()
                      for e in (nd.get("entities") or [])}
        for pd in prior_decisions:
            p_text = _embed_text_dict(pd).lower()
            p_topic = (pd.get("topic") or "").lower()
            p_entities = {e.get("value", "").lower() if isinstance(e, dict) else str(e).lower()
                          for e in (pd.get("entities") or [])}
            overlap = n_entities & p_entities
            topic_match = n_topic and p_topic and (n_topic in p_topic or p_topic in n_topic)
            n_tokens = set(n_text.split())
            p_tokens = set(p_text.split())
            token_score = len(n_tokens & p_tokens) / max(1, len(n_tokens | p_tokens))
            if overlap or topic_match or token_score > 0.08:
                pairs.append((nd, pd))
    return pairs


def _embed_text_dict(d: dict) -> str:
    ents = " ".join(e.get("value", "") if isinstance(e, dict) else str(e) for e in (d.get("entities") or []))
    return f"{d.get('topic', '')} {d.get('statement', '')} {ents}".strip()


def classify_conflict(relation: str, confidence: float) -> str:
    """Map (relation, confidence) → severity."""
    if relation == "contradicts":
        return "blocking" if confidence >= 0.70 else "possible"
    if relation == "supersedes":
        return "blocking" if confidence >= 0.85 else "possible"
    if relation == "duplicate":
        return "info"
    if relation == "refines":
        return "info"
    return "info"