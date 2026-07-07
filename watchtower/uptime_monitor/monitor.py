"""Linus uptime monitor — long-running website availability watcher.

Runs forever: on every interval it checks each configured site, folds the
result into flap-resistant state, and emits a JSON event whenever a site goes
down or recovers. Designed to run as a service (see the systemd unit and
README in this directory).

Run from this directory:

    python monitor.py

or as a module from the repo root:

    python -m watchtower.uptime_monitor.monitor
"""

from __future__ import annotations

import logging
import signal
import sys
import time

try:  # package-relative when run as a module
    from .alerts import build_event, emit
    from .checker import check_site
    from .config import ConfigError, Settings, load_settings
    from .state import StateStore
except ImportError:  # direct `python monitor.py`
    from alerts import build_event, emit
    from checker import check_site
    from config import ConfigError, Settings, load_settings
    from state import StateStore


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("uptime.monitor")

_STOP = False


def _handle_signal(signum, _frame) -> None:
    global _STOP
    LOGGER.info("Received signal %s; shutting down after this cycle.", signum)
    _STOP = True


def check_all(settings: Settings, state: StateStore) -> None:
    """Check every site once and emit any confirmed transitions."""
    for site in settings.sites:
        result = check_site(
            site.url,
            timeout_seconds=settings.timeout_seconds,
            expected_status=site.expected_status,
            keyword=site.keyword,
        )
        transition = state.record(
            site.name,
            ok=result.ok,
            status=result.status,
            latency_ms=result.latency_ms,
            error=result.error,
        )

        if transition:
            since = state.sites[site.name].last_change
            event = build_event(transition, site.name, site.url, result.as_dict(), since)
            emit(event, settings.webhook_url)
            level = logging.ERROR if transition == "site_down" else logging.INFO
            LOGGER.log(level, "%s: %s (%s)", transition, site.name, result.error or "ok")
        else:
            LOGGER.info(
                "%s %s (status=%s, %sms)",
                "UP  " if result.ok else "DOWN",
                site.name,
                result.status,
                result.latency_ms,
            )

    state.save()


def main() -> int:
    # --once: run a single check cycle and exit. Use this on hosts where a
    # persistent process isn't allowed (e.g. Bluehost / shared cPanel hosting)
    # by driving it from cron. Without it, the monitor runs forever as a daemon.
    run_once = "--once" in sys.argv[1:]

    try:
        settings = load_settings()
    except ConfigError as exc:
        LOGGER.error("%s", exc)
        return 1

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    state = StateStore(
        path=settings.state_file,
        failures_before_down=settings.failures_before_down,
        successes_before_up=settings.successes_before_up,
    )
    state.load()

    if run_once:
        LOGGER.info("Running a single check cycle (--once): %d site(s).", len(settings.sites))
        try:
            check_all(settings, state)
        except Exception:
            LOGGER.exception("Unexpected error during check cycle.")
            return 1
        return 0

    LOGGER.info(
        "Starting Linus uptime monitor: %d site(s), every %ds, %ds timeout.",
        len(settings.sites),
        settings.check_interval_seconds,
        int(settings.timeout_seconds),
    )

    while not _STOP:
        try:
            check_all(settings, state)
        except Exception:  # never let one bad cycle kill the service
            LOGGER.exception("Unexpected error during check cycle; will retry next interval.")

        # Sleep in short slices so a stop signal is honored promptly.
        slept = 0.0
        while slept < settings.check_interval_seconds and not _STOP:
            time.sleep(min(1.0, settings.check_interval_seconds - slept))
            slept += 1.0

    LOGGER.info("Linus uptime monitor stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
