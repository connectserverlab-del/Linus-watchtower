from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_JQL = "assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC"
DEFAULT_POLL_INTERVAL_SECONDS = 60
DEFAULT_STATE_FILE = Path(__file__).with_name("state.json")


@dataclass(frozen=True)
class Settings:
    jira_base_url: str
    jira_email: str
    jira_api_token: str
    jira_poll_interval_seconds: int
    jira_jql: str
    state_file: Path = DEFAULT_STATE_FILE


class ConfigError(ValueError):
    pass


def _clean_base_url(value: str) -> str:
    return value.strip().rstrip("/")


def _parse_poll_interval(value: str | None) -> int:
    if not value:
        return DEFAULT_POLL_INTERVAL_SECONDS

    try:
        interval = int(value)
    except ValueError as exc:
        raise ConfigError("JIRA_POLL_INTERVAL_SECONDS must be an integer.") from exc

    if interval < 1:
        raise ConfigError("JIRA_POLL_INTERVAL_SECONDS must be at least 1.")

    return interval


def load_settings() -> Settings:
    load_dotenv()

    jira_base_url = _clean_base_url(os.getenv("JIRA_BASE_URL", ""))
    jira_email = os.getenv("JIRA_EMAIL", "").strip()
    jira_api_token = os.getenv("JIRA_API_TOKEN", "").strip()
    jira_jql = os.getenv("JIRA_JQL", DEFAULT_JQL).strip() or DEFAULT_JQL
    poll_interval = _parse_poll_interval(os.getenv("JIRA_POLL_INTERVAL_SECONDS"))

    missing = [
        name
        for name, value in {
            "JIRA_BASE_URL": jira_base_url,
            "JIRA_EMAIL": jira_email,
            "JIRA_API_TOKEN": jira_api_token,
        }.items()
        if not value
    ]
    if missing:
        names = ", ".join(missing)
        raise ConfigError(f"Missing required environment variable(s): {names}")

    return Settings(
        jira_base_url=jira_base_url,
        jira_email=jira_email,
        jira_api_token=jira_api_token,
        jira_poll_interval_seconds=poll_interval,
        jira_jql=jira_jql,
    )
