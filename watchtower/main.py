from __future__ import annotations

import logging
import time

import requests

try:
    from .config import ConfigError, load_settings
    from .event_emitter import EventEmitter, build_ticket_event
    from .jira_client import JiraClient
    from .state_store import StateStore
except ImportError:
    from config import ConfigError, load_settings
    from event_emitter import EventEmitter, build_ticket_event
    from jira_client import JiraClient
    from state_store import StateStore


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger(__name__)


def poll_once(
    jira_client: JiraClient,
    state_store: StateStore,
    event_emitter: EventEmitter,
    jql: str,
) -> int:
    tickets = jira_client.search_tickets(jql)
    emitted_count = 0

    for ticket in tickets:
        ticket_key = ticket.get("key") or ""
        updated = ticket.get("updated") or ""
        if not ticket_key:
            LOGGER.warning("Skipping Jira issue without a key: %s", ticket)
            continue

        change_type = state_store.detect_change(ticket_key=ticket_key, updated=updated)
        if change_type == "new":
            event = build_ticket_event("ticket_created_or_seen", ticket)
            event_emitter.emit(event)
            emitted_count += 1
        elif change_type == "updated":
            event = build_ticket_event("ticket_updated", ticket)
            event_emitter.emit(event)
            emitted_count += 1

        state_store.update_ticket(ticket_key=ticket_key, updated=updated)

    state_store.save()
    return emitted_count


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        LOGGER.error("%s", exc)
        return 1

    LOGGER.info("Starting Watchtower Jira observer.")
    LOGGER.info("Jira base URL: %s", settings.jira_base_url)
    LOGGER.info("Poll interval: %s seconds", settings.jira_poll_interval_seconds)
    LOGGER.info("State file: %s", settings.state_file)

    jira_client = JiraClient(
        base_url=settings.jira_base_url,
        email=settings.jira_email,
        api_token=settings.jira_api_token,
    )
    state_store = StateStore(settings.state_file)
    event_emitter = EventEmitter()
    state_store.load()

    try:
        while True:
            try:
                emitted_count = poll_once(
                    jira_client=jira_client,
                    state_store=state_store,
                    event_emitter=event_emitter,
                    jql=settings.jira_jql,
                )
                LOGGER.info("Poll complete. Emitted %s event(s).", emitted_count)
            except requests.RequestException as exc:
                LOGGER.warning("Jira request failed; will retry next poll: %s", exc)
            except Exception:
                LOGGER.exception("Unexpected error during poll; will retry next poll.")

            time.sleep(settings.jira_poll_interval_seconds)
    except KeyboardInterrupt:
        LOGGER.info("Watchtower stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
