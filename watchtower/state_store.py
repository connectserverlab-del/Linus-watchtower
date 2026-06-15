from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal


LOGGER = logging.getLogger(__name__)

TicketState = dict[str, str]
ChangeType = Literal["new", "updated", "unchanged"]


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.state: TicketState = {}

    def load(self) -> None:
        if not self.path.exists():
            self.state = {}
            return

        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("Could not load state file %s: %s", self.path, exc)
            self.state = {}
            return

        if not isinstance(data, dict):
            LOGGER.warning("State file %s did not contain a JSON object.", self.path)
            self.state = {}
            return

        self.state = {
            str(ticket_key): str(updated)
            for ticket_key, updated in data.items()
            if ticket_key and updated
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(f"{self.path.suffix}.tmp")

        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(self.state, file, indent=2, sort_keys=True)
            file.write("\n")

        temporary_path.replace(self.path)

    def detect_change(self, ticket_key: str, updated: str) -> ChangeType:
        previous_updated = self.state.get(ticket_key)
        if previous_updated is None:
            return "new"
        if updated and updated > previous_updated:
            return "updated"
        return "unchanged"

    def update_ticket(self, ticket_key: str, updated: str) -> None:
        if ticket_key and updated:
            self.state[ticket_key] = updated
