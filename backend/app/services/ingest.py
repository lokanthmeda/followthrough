"""Ingestion: turn raw transcript text into normalized utterances.

Handles paste/upload (Name: prefixes), VTT/SRT cues, and dictated recaps.
Speaker labels are resolved to Person rows lazily by the resolver.
"""
import re
from typing import Any
from uuid import uuid4 as _uuid

from ..models import Utterance


SpeakerLine = re.compile(r"^\s*(?P<speaker>[^:]+?)\s*[:|\-]\s*(?P<text>.*)$", re.MULTILINE)


def normalize_transcript(text: str) -> list[dict]:
    """Return a list of {speaker, text_raw} utterances.

    Strategy:
      1. If the text looks like VTT/SRT (cue timestamps), parse cues.
      2. Otherwise split on "Speaker:" prefixes.
      3. If no speaker labels are found, treat the whole text as a single
         speaker-less utterance (Channel B dictated recap).
    """
    cues = _parse_cues(text)
    if cues:
        return [{"speaker": c.get("speaker"), "text_raw": c["text"]} for c in cues]

    labeled = _parse_labeled(text)
    if labeled:
        return labeled

    # No speaker attribution — single dictated recap
    return [{"speaker": None, "text_raw": text.strip()}]


def _parse_labeled(text: str) -> list[dict]:
    out: list[dict] = []
    cur: dict | None = None
    for line in text.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        m = SpeakerLine.match(line)
        if m:
            cur = {"speaker": m.group("speaker").strip(), "text_raw": m.group("text").strip()}
            out.append(cur)
        elif cur is not None:
            cur["text_raw"] += " " + line.strip()
    return out


_CUE = re.compile(
    r"(?:(?P<start>\d{1,2}:\d{2}:\d{2}[.,]\d{3})\s*-->?\s*(?P<end>\d{1,2}:\d{2}:\d{2}[.,]\d{3}))?"
    r"\s*(?P<speaker>[^\n]+?)?\s*\n(?P<text>.+?)(?=\n\d{1,2}:\d{2}:\d{2}[.,]\d{3}\s*-->|\Z)",
    re.DOTALL,
)


def _parse_cues(text: str) -> list[dict]:
    if not re.search(r"\d{1,2}:\d{2}:\d{2}[.,]\d{3}\s*-->", text):
        return []
    out: list[dict] = []
    for m in _CUE.finditer(text):
        sp = m.group("speaker")
        if sp:
            sp = re.sub(r"^\s*<[^>]+>\s*", "", sp).strip()
        out.append({"speaker": sp, "text": m.group("text").strip()})
    return out


def clean_disfluencies(text: str) -> str:
    """Strip fillers / false starts while keeping the raw text for evidence.

    This is a deterministic rule-based pass; the LLM extractor also handles
    self-correction semantics.
    """
    t = text
    # remove parenthetical fillers
    t = re.sub(r"\b(um|uh|uhm|ah|like|you know|i mean|so)\b", "", t, flags=re.IGNORECASE)
    # collapse repeated whitespace
    t = re.sub(r"\s+", " ", t).strip()
    # trim leading/trailing commas left behind
    t = re.sub(r"\s*,\s*,", ",", t)
    return t


def build_utterances(meeting_id: str, raw_text: str, start_seq: int = 0) -> list[Utterance]:
    norm = normalize_transcript(raw_text)
    out: list[Utterance] = []
    for i, u in enumerate(norm):
        out.append(
            Utterance(
                id=str(_uuid()),
                meeting_id=meeting_id,
                seq=start_seq + i,
                speaker_label=u.get("speaker"),
                person_id=None,
                text_raw=u["text_raw"],
                text_clean=clean_disfluencies(u["text_raw"]),
            )
        )
    return out