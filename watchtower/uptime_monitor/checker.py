"""HTTP reachability check for a single site.

Uses only the Python standard library so the monitor can run on any server
without installing dependencies.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class CheckResult:
    """Outcome of a single site check."""

    ok: bool
    status: int | None
    latency_ms: int | None
    error: str | None

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


def check_site(
    url: str,
    *,
    timeout_seconds: float,
    expected_status: int | None = None,
    keyword: str | None = None,
    user_agent: str = "Linus-Watchtower/1.0 (+uptime-monitor)",
) -> CheckResult:
    """Fetch ``url`` once and decide whether the site is healthy.

    A site is considered UP when:
      * the request completes without a network/timeout error, AND
      * the HTTP status matches ``expected_status`` (or is 2xx/3xx when no
        expected status is configured), AND
      * ``keyword`` (if given) appears in the response body.

    Never raises for expected failure modes — a down site is a normal result,
    returned as ``ok=False`` with an ``error`` describing why.
    """
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": user_agent})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = response.status
            body = b""
            if keyword:
                # Only read the body when we actually need to inspect it.
                body = response.read(1_000_000)  # cap at 1 MB
    except urllib.error.HTTPError as exc:
        # The server answered, just not with a success code.
        latency_ms = int((time.monotonic() - start) * 1000)
        status = exc.code
        ok = expected_status is not None and status == expected_status
        return CheckResult(
            ok=ok,
            status=status,
            latency_ms=latency_ms,
            error=None if ok else f"HTTP {status}",
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        reason = getattr(exc, "reason", exc)
        return CheckResult(ok=False, status=None, latency_ms=latency_ms, error=f"{reason}")

    latency_ms = int((time.monotonic() - start) * 1000)

    if expected_status is not None:
        status_ok = status == expected_status
    else:
        status_ok = 200 <= status < 400

    if not status_ok:
        return CheckResult(ok=False, status=status, latency_ms=latency_ms, error=f"HTTP {status}")

    if keyword and keyword.encode("utf-8", "ignore") not in body:
        return CheckResult(
            ok=False,
            status=status,
            latency_ms=latency_ms,
            error=f"keyword {keyword!r} not found in body",
        )

    return CheckResult(ok=True, status=status, latency_ms=latency_ms, error=None)
