# Watchtower

Watchtower is a local Jira Observer service. It polls the Jira REST API, detects new or updated Jira tickets by comparing them with local saved state, and emits clean JSON events that can later be routed to a Core Orchestrator and AI divisions such as Seros, Zen, Aegis, Trule, and Dios.

Watchtower is infrastructure only. It does not make AI decisions, route work, run a web UI, or store data in a database.

## Requirements

- Python 3.11+
- Jira Cloud site access
- Jira API token

## Install

From this directory:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If your system uses `python3` for Python 3.11+, this also works:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Create a Jira API Token

1. Go to `https://id.atlassian.com/manage-profile/security/api-tokens`.
2. Select `Create API token`.
3. Give it a label such as `Watchtower local observer`.
4. Copy the token and keep it private.

## Configure

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_POLL_INTERVAL_SECONDS=60
JIRA_JQL=assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC
```

`JIRA_JQL` controls which tickets Watchtower observes. The default query watches active tickets assigned to the current Jira user.

## Run

From the parent repository directory:

```bash
python -m watchtower.main
```

Or from this `watchtower` directory:

```bash
python main.py
```

Stop the observer with `Ctrl+C`.

## State

Watchtower stores the latest observed Jira `updated` timestamp for each issue key in `state.json`:

```json
{
  "SQC-656": "2026-06-15T00:40:00.000-0400"
}
```

This keeps the MVP simple and human-readable.

## Example Event

Each detected new or updated ticket is printed as a JSON object:

```json
{
  "source": "jira",
  "event_type": "ticket_updated",
  "ticket_key": "SQC-656",
  "summary": "Fix service worker issue",
  "status": "In Progress",
  "priority": "Medium",
  "assignee": "Michael Pou",
  "reporter": "Manager Name",
  "labels": ["frontend", "bug"],
  "created": "2026-06-15T00:20:00.000-0400",
  "updated": "2026-06-15T00:40:00.000-0400",
  "raw_url": "https://your-domain.atlassian.net/browse/SQC-656"
}
```

New tickets emit `ticket_created_or_seen`. Existing tickets with a newer Jira `updated` timestamp emit `ticket_updated`.

## Future Architecture

The MVP emits events to stdout. Later, `event_emitter.py` can be replaced or extended to publish events to an HTTP endpoint, message queue, file sink, or Core Orchestrator.

The intended future flow:

```text
Jira -> Watchtower -> Core Orchestrator -> Seros / Zen / Aegis / Trule / Dios
```

Watchtower should remain a focused observer. AI division logic belongs downstream.
