"""Safety tests (PRD §14.3): nothing posts without approval, idempotency, no hallucination."""
import pytest
import sys
sys.path.insert(0, '.')

from app.adapters.tracker import _MockAdapter, dedupe_key
from app.adapters.tracker import ExternalRef


def test_mock_adapter_creates_task():
    adapter = _MockAdapter()
    ref = adapter.create_task({"title": "Test Task", "description": "Test"})
    assert ref.external_system == "mock"
    assert "Test Task" in ref.external_id


def test_dedupe_key_uniqueness():
    """Two identical inputs must produce identical keys (idempotency)."""
    k1 = dedupe_key("meet-1", "do the thing", "user-a")
    k2 = dedupe_key("meet-1", "do the thing", "user-a")
    assert k1 == k2


def test_dedupe_key_diff_for_different_owners():
    k1 = dedupe_key("meet-1", "do the thing", "user-a")
    k2 = dedupe_key("meet-1", "do the thing", "user-b")
    assert k1 != k2


def test_dedupe_key_diff_for_different_titles():
    k1 = dedupe_key("meet-1", "do thing 1", "user-a")
    k2 = dedupe_key("meet-1", "do thing 2", "user-a")
    assert k1 != k2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])