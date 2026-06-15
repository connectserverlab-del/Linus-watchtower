from __future__ import annotations

import json
from typing import Any


class EventEmitter:
    def emit(self, event: dict[str, Any]) -> None:
        print(json.dumps(event, ensure_ascii=False, sort_keys=True), flush=True)


def build_ticket_event(event_type: str, ticket: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "jira",
        "event_type": event_type,
        "ticket_key": ticket.get("key") or "",
        "summary": ticket.get("summary") or "",
        "status": ticket.get("status") or "",
        "priority": ticket.get("priority") or "",
        "assignee": ticket.get("assignee") or "",
        "reporter": ticket.get("reporter") or "",
        "labels": ticket.get("labels") or [],
        "created": ticket.get("created") or "",
        "updated": ticket.get("updated") or "",
        "raw_url": ticket.get("raw_url") or "",
    }
