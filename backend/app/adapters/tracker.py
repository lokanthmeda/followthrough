"""Tracker adapter interface + Linear implementation (PRD §6.5)."""
import hashlib
import json
from typing import Protocol

import httpx

from ..config import settings


class ExternalRef:
    def __init__(self, external_system: str, external_id: str, external_url: str):
        self.external_system = external_system
        self.external_id = external_id
        self.external_url = external_url


class TaskStatus:
    def __init__(self, done: bool, state: str | None = None):
        self.done = done
        self.state = state


class TrackerAdapter(Protocol):
    def create_task(self, task: dict) -> ExternalRef: ...
    def get_task_status(self, ref: ExternalRef) -> TaskStatus: ...
    def find_user_by_email(self, email: str): ...
    def search_similar(self, title: str) -> list: ...


class LinearAdapter:
    def __init__(self, api_key: str | None = None, api_url: str | None = None):
        self.api_key = api_key or settings.linear_api_key
        self.api_url = api_url or settings.linear_api_url

    def _headers(self) -> dict:
        return {"Authorization": self.api_key, "Content-Type": "application/json"}

    def create_task(self, task: dict) -> ExternalRef:
        """Create a Linear issue. Raises if no API key configured (caller must handle)."""
        if not self.api_key:
            raise RuntimeError("Linear API key not configured")

        query = """
        mutation IssueCreate($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue { id identifier url title }
          }
        }
        """
        body = {
            "teamId": task.get("team_id"),
            "title": task["title"],
            "description": task.get("description", ""),
            "assigneeId": task.get("assignee_id"),
            "dueDate": task.get("due_date"),
            "labelIds": task.get("label_ids", []),
        }
        r = httpx.post(
            f"{self.api_url}/graphql",
            headers=self._headers(),
            json={"query": query, "variables": {"input": body}},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("data", {}).get("issueCreate", {}).get("success"):
            raise RuntimeError(f"Linear issueCreate failed: {data}")
        issue = data["data"]["issueCreate"]["issue"]
        return ExternalRef("linear", issue["id"], issue.get("url", ""))

    def get_task_status(self, ref: ExternalRef) -> TaskStatus:
        if not self.api_key:
            return TaskStatus(done=False)
        query = "query($id: String!) { issue(id: $id) { state { name } } }"
        r = httpx.post(f"{self.api_url}/graphql", headers=self._headers(),
                       json={"query": query, "variables": {"id": ref.external_id}}, timeout=30)
        r.raise_for_status()
        state = r.json()["data"]["issue"]["state"]["name"].lower()
        return TaskStatus(done=state in ("done", "completed", "cancelled"), state=state)

    def find_user_by_email(self, email: str):
        if not self.api_key:
            return None
        query = "query($email: String!) { user(email: $email) { id name email } }"
        r = httpx.post(f"{self.api_url}/graphql", headers=self._headers(),
                       json={"query": query, "variables": {"email": email}}, timeout=30)
        r.raise_for_status()
        return r.json().get("data", {}).get("user")

    def search_similar(self, title: str) -> list:
        return []


def dedupe_key(meeting_id: str, title: str, owner: str | None) -> str:
    """Deterministic idempotency key (PRD FR-5.6)."""
    raw = f"{meeting_id}|{(title or '').strip().lower()}|{(owner or '').strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def get_adapter() -> TrackerAdapter:
    if settings.tracker_provider == "linear" and settings.linear_api_key:
        return LinearAdapter()
    if settings.tracker_provider == "github" and settings.linear_api_key:
        return _GitHubAdapter()
    return _MockAdapter()


class _MockAdapter:
    """Fallback adapter used when no tracker is configured (demo-safe)."""

    def create_task(self, task: dict) -> ExternalRef:
        task_id = f"TASK-{hashlib.sha256(task['title'].encode()).hexdigest()[:6].upper()}"
        return ExternalRef("mock", task_id, f"https://tracker.followthrough.internal/issue/{task_id}")

    def get_task_status(self, ref: ExternalRef) -> TaskStatus:
        return TaskStatus(done=False)

    def find_user_by_email(self, email: str):
        return {"id": "mock", "name": email, "email": email}

    def search_similar(self, title: str) -> list:
        return []


class _GitHubAdapter:
    def __init__(self):
        self.api_key = settings.linear_api_key  # reuse for GH token in demo

    def create_task(self, task: dict) -> ExternalRef:
        if not self.api_key:
            raise RuntimeError("GitHub token not configured")
        r = httpx.post(
            "https://api.github.com/repos/placeholder/issues",
            headers={"Authorization": f"token {self.api_key}", "Content-Type": "application/json"},
            json={"title": task["title"], "body": task.get("description", "")},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return ExternalRef("github", str(data["id"]), data.get("html_url", ""))

    def get_task_status(self, ref: ExternalRef) -> TaskStatus:
        return TaskStatus(done=False)

    def find_user_by_email(self, email: str):
        return None

    def search_similar(self, title: str) -> list:
        return []