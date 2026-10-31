"""Tests for the Followthrough pipeline."""
import asyncio
import pytest
import sys
sys.path.insert(0, '.')

from app.services.ingest import normalize_transcript, clean_disfluencies, build_utterances
from app.services.extract import resolve_relative_date
from app.adapters.tracker import dedupe_key
from datetime import datetime


def test_normalize_transcript_labeled():
    text = "Arjun: We will price strictly usage-based.\nMeera: Agreed."
    result = normalize_transcript(text)
    assert len(result) == 2
    assert result[0]["speaker"] == "Arjun"
    assert result[1]["speaker"] == "Meera"


def test_normalize_transcript_no_speaker():
    text = "Just a plain dictated recap with no speaker labels."
    result = normalize_transcript(text)
    assert len(result) == 1
    assert result[0]["speaker"] is None
    assert "recap" in result[0]["text_raw"]


def test_clean_disfluencies():
    text = "um, we will go with hybrid, actually base fee plus usage"
    cleaned = clean_disfluencies(text)
    assert "um" not in cleaned
    assert "hybrid" in cleaned


def test_resolve_relative_date_next_monday():
    anchor = datetime(2026, 10, 31, 10, 0, 0)  # Saturday
    date, phrase = resolve_relative_date("next Monday", anchor)
    assert date == "2026-11-02"


def test_resolve_relative_date_by_friday():
    anchor = datetime(2026, 10, 31, 10, 0, 0)
    date, phrase = resolve_relative_date("by Friday", anchor)
    assert date == "2026-11-06"


def test_dedupe_key_is_deterministic():
    k1 = dedupe_key("m1", "Update API", "ravi")
    k2 = dedupe_key("m1", "Update API", "ravi")
    assert k1 == k2
    k3 = dedupe_key("m1", "Update API", "meera")
    assert k1 != k3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])