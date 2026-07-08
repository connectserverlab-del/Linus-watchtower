"""Emit uptime events.

Every transition is printed to stdout as a single-line JSON object (matching
Watchtower's event style) and, if a webhook URL is configured, POSTed there.
Stdlib only, so no dependencies to install on the server.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone

LOGGER = logging.getLogger("uptime.alerts")


def build_event(event_type: str, site_name: str, url: str, result: dict, since: str | None) -> dict:
    """Assemble a clean event payload for a site transition."""
    return {
        "source": "uptime",
        "event_type": event_type,  # "site_down" | "site_recovered"
        "site": site_name,
        "url": url,
        "status": result.get("status"),
        "latency_ms": result.get("latency_ms"),
        "error": result.get("error"),
        "since": since,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def emit(event: dict, webhook_url: str | None = None) -> None:
    """Print the event and best-effort POST it to a webhook."""
    line = json.dumps(event)
    # stdout is the primary sink (pipe it to a log shipper / journald).
    print(line, flush=True)

    if not webhook_url:
        return
    data = line.encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            pass
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # A failing alert channel must never crash the monitor.
        LOGGER.warning("Webhook delivery failed: %s", exc)
