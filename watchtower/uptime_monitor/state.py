"""Per-site up/down state with flap-resistant transition detection.

State is persisted as human-readable JSON (matching Watchtower's `state.json`
convention) so it survives restarts and can be inspected by hand.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SiteState:
    status: str = "unknown"  # "up" | "down" | "unknown"
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_change: str | None = None
    last_checked: str | None = None
    last_status_code: int | None = None
    last_latency_ms: int | None = None
    last_error: str | None = None


@dataclass
class StateStore:
    """Tracks each site's health and decides when a real transition happened.

    A transition to DOWN is only reported after ``failures_before_down``
    consecutive failures, and back to UP after ``successes_before_up``
    consecutive successes — this absorbs single blips instead of alerting on
    every flap.
    """

    path: str
    failures_before_down: int = 2
    successes_before_up: int = 1
    sites: dict[str, SiteState] = field(default_factory=dict)

    def load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (json.JSONDecodeError, OSError):
            # Corrupt/unreadable state should not stop monitoring — start fresh.
            return
        for name, data in raw.items():
            if isinstance(data, dict):
                self.sites[name] = SiteState(**{k: data.get(k) for k in SiteState().__dict__})

    def save(self) -> None:
        serializable = {name: asdict(state) for name, state in self.sites.items()}
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(serializable, handle, indent=2, sort_keys=True)
        os.replace(tmp, self.path)  # atomic write

    def record(self, name: str, *, ok: bool, status, latency_ms, error) -> str | None:
        """Fold one check result into the site's state.

        Returns a transition string ("site_down" or "site_recovered") when the
        confirmed status flips, otherwise ``None``.
        """
        state = self.sites.setdefault(name, SiteState())
        state.last_checked = _now_iso()
        state.last_status_code = status
        state.last_latency_ms = latency_ms
        state.last_error = error

        transition: str | None = None

        if ok:
            state.consecutive_successes += 1
            state.consecutive_failures = 0
            if state.status != "up" and state.consecutive_successes >= self.successes_before_up:
                # "unknown -> up" on first run is not an alert-worthy recovery.
                transition = "site_recovered" if state.status == "down" else None
                state.status = "up"
                state.last_change = _now_iso()
        else:
            state.consecutive_failures += 1
            state.consecutive_successes = 0
            if state.status != "down" and state.consecutive_failures >= self.failures_before_down:
                transition = "site_down"
                state.status = "down"
                state.last_change = _now_iso()

        return transition
