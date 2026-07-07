"""Configuration loading for the uptime monitor.

Config is a JSON file (see ``sites.example.json``). A few operational knobs can
be overridden by environment variables so the same config file works across
environments:

  LINUS_UPTIME_CONFIG   path to the JSON config file (default: sites.json)
  LINUS_WEBHOOK_URL     overrides ``webhook_url`` from the file
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


class ConfigError(Exception):
    """Raised when the configuration is missing or invalid."""


@dataclass
class Site:
    name: str
    url: str
    expected_status: int | None = None
    keyword: str | None = None


@dataclass
class Settings:
    check_interval_seconds: int = 60
    timeout_seconds: float = 10.0
    failures_before_down: int = 2
    successes_before_up: int = 1
    state_file: str = "uptime_state.json"
    webhook_url: str | None = None
    sites: list[Site] = field(default_factory=list)


def load_settings(path: str | None = None) -> Settings:
    path = path or os.environ.get("LINUS_UPTIME_CONFIG", "sites.json")
    if not os.path.exists(path):
        raise ConfigError(
            f"Config file not found: {path}. Copy sites.example.json to sites.json and edit it."
        )
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config file {path} is not valid JSON: {exc}") from exc

    sites_raw = raw.get("sites")
    if not isinstance(sites_raw, list) or not sites_raw:
        raise ConfigError("Config must include a non-empty 'sites' list.")

    sites: list[Site] = []
    for entry in sites_raw:
        if not isinstance(entry, dict) or "url" not in entry:
            raise ConfigError(f"Each site needs at least a 'url': {entry!r}")
        sites.append(
            Site(
                name=entry.get("name") or entry["url"],
                url=entry["url"],
                expected_status=entry.get("expected_status"),
                keyword=entry.get("keyword"),
            )
        )

    webhook = os.environ.get("LINUS_WEBHOOK_URL") or raw.get("webhook_url") or None

    return Settings(
        check_interval_seconds=int(raw.get("check_interval_seconds", 60)),
        timeout_seconds=float(raw.get("timeout_seconds", 10)),
        failures_before_down=int(raw.get("failures_before_down", 2)),
        successes_before_up=int(raw.get("successes_before_up", 1)),
        state_file=raw.get("state_file", "uptime_state.json"),
        webhook_url=webhook,
        sites=sites,
    )
