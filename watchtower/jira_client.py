from __future__ import annotations

import logging
from typing import Any

import requests
from requests.auth import HTTPBasicAuth


LOGGER = logging.getLogger(__name__)

JIRA_FIELDS = [
    "summary",
    "description",
    "status",
    "assignee",
    "reporter",
    "priority",
    "labels",
    "updated",
    "created",
]


Ticket = dict[str, Any]


class JiraClient:
    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        timeout_seconds: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(email, api_token)
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def search_tickets(self, jql: str, max_results: int = 50) -> list[Ticket]:
        try:
            issues = self._search_with_jql_endpoint(jql=jql, max_results=max_results)
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code not in {400, 404, 410}:
                raise

            LOGGER.info(
                "Jira /search/jql endpoint unavailable; falling back to /search."
            )
            issues = self._search_with_legacy_endpoint(jql=jql, max_results=max_results)

        return [self._normalize_issue(issue) for issue in issues]

    def _search_with_jql_endpoint(self, jql: str, max_results: int) -> list[dict[str, Any]]:
        url = f"{self.base_url}/rest/api/3/search/jql"
        params: dict[str, Any] = {
            "jql": jql,
            "maxResults": max_results,
            "fields": ",".join(JIRA_FIELDS),
        }
        issues: list[dict[str, Any]] = []

        while True:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()

            issues.extend(payload.get("issues", []))
            next_page_token = payload.get("nextPageToken")
            if not next_page_token:
                break

            params["nextPageToken"] = next_page_token

        return issues

    def _search_with_legacy_endpoint(
        self, jql: str, max_results: int
    ) -> list[dict[str, Any]]:
        url = f"{self.base_url}/rest/api/3/search"
        start_at = 0
        issues: list[dict[str, Any]] = []

        while True:
            payload = {
                "jql": jql,
                "startAt": start_at,
                "maxResults": max_results,
                "fields": JIRA_FIELDS,
            }
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()

            page_issues = data.get("issues", [])
            issues.extend(page_issues)

            total = data.get("total", len(issues))
            if not page_issues or len(issues) >= total:
                break

            start_at += len(page_issues)

        return issues

    def _normalize_issue(self, issue: dict[str, Any]) -> Ticket:
        fields = issue.get("fields") or {}
        ticket_key = issue.get("key", "")

        return {
            "key": ticket_key,
            "summary": fields.get("summary") or "",
            "description": fields.get("description"),
            "status": self._name_from_field(fields.get("status")),
            "assignee": self._display_name_from_user(fields.get("assignee")),
            "reporter": self._display_name_from_user(fields.get("reporter")),
            "priority": self._name_from_field(fields.get("priority")),
            "labels": fields.get("labels") or [],
            "updated": fields.get("updated") or "",
            "created": fields.get("created") or "",
            "raw_url": f"{self.base_url}/browse/{ticket_key}" if ticket_key else "",
        }

    @staticmethod
    def _name_from_field(value: dict[str, Any] | None) -> str:
        if not value:
            return ""
        return str(value.get("name") or "")

    @staticmethod
    def _display_name_from_user(value: dict[str, Any] | None) -> str:
        if not value:
            return ""
        return str(value.get("displayName") or value.get("emailAddress") or "")
