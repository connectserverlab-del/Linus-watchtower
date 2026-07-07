# Linus Uptime Monitor

A long-running process that continuously checks whether your sites are up,
detects up↔down transitions (with flap protection), and emits a JSON event on
every change. Part of **Linus** — the watchdog that currently monitors
performance across Standard Sites and is intended to grow into its own product.

**Zero dependencies** — pure Python standard library (Python 3.8+). Drop it on
any server and run it, as a long-running daemon or a cron one-shot.

## Quick start

```bash
cd watchtower/uptime_monitor
cp sites.example.json sites.json      # edit with your sites
python3 monitor.py
```

Stop with `Ctrl+C`. The monitor checks every site on each interval and logs a
line per site; a **transition** (down or recovered) additionally emits a JSON
event to stdout and (optionally) a webhook.

## Configuration (`sites.json`)

```json
{
  "check_interval_seconds": 60,
  "timeout_seconds": 10,
  "failures_before_down": 2,
  "successes_before_up": 1,
  "state_file": "uptime_state.json",
  "webhook_url": "",
  "sites": [
    { "name": "Marketing", "url": "https://example.com", "expected_status": 200 },
    { "name": "App",       "url": "https://app.example.com", "keyword": "Sign in" }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `check_interval_seconds` | How often to check every site. |
| `timeout_seconds` | Per-request timeout. |
| `failures_before_down` | Consecutive failures before a site is declared **down** (absorbs blips). |
| `successes_before_up` | Consecutive successes before a down site is declared **recovered**. |
| `state_file` | Where up/down state is persisted (survives restarts). |
| `webhook_url` | Optional. Each transition event is POSTed here as JSON. |
| `sites[].expected_status` | Optional. If set, only this status is healthy; otherwise any 2xx/3xx is healthy. |
| `sites[].keyword` | Optional. Response body must contain this string to be healthy (catches "200 but broken" pages). |

Environment overrides: `LINUS_UPTIME_CONFIG` (config path), `LINUS_WEBHOOK_URL`.

## Event format

A transition prints one JSON line (and POSTs it to the webhook if configured):

```json
{"source":"uptime","event_type":"site_down","site":"App","url":"https://app.example.com","status":503,"latency_ms":142,"error":"HTTP 503","since":"2026-07-07T22:40:00+00:00","timestamp":"2026-07-07T22:40:00+00:00"}
```

`event_type` is `site_down` or `site_recovered`. This mirrors the event style of
the parent Watchtower observer, so downstream routing can treat both the same way.

## Running as a service (systemd)

```bash
sudo cp linus-uptime.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now linus-uptime
journalctl -u linus-uptime -f          # follow the logs
```

Edit `User`, `WorkingDirectory`, and (optionally) `LINUS_WEBHOOK_URL` in the unit
file to match your deployment. `Restart=always` keeps it running across crashes
and reboots.

## Running on shared hosting (Bluehost / cPanel) — use cron

Shared hosts typically don't allow a persistent background process (no systemd,
long-running scripts get killed). Run a **one-shot check on a schedule** instead:

```bash
python3 monitor.py --once
```

`--once` runs a single cycle and exits, updating the same `uptime_state.json`,
so transition detection (down/recovered) still works across runs. Add a cron job
(cPanel → *Cron Jobs*), e.g. every 5 minutes:

```cron
*/5 * * * * cd /home/USER/linus/uptime_monitor && /usr/bin/python3 monitor.py --once >> uptime.log 2>&1
```

Notes for Bluehost:
- Use the Python path from cPanel's *Setup Python App* if the system `python3`
  is too old (this monitor needs 3.8+).
- Set the check interval in `sites.json` to match (or exceed) your cron cadence —
  with `--once`, cron *is* the interval, so `check_interval_seconds` is ignored.
- Configure `webhook_url` (or `LINUS_WEBHOOK_URL`) so you're alerted even though
  stdout goes to `uptime.log`.

## How "down" is decided

A site is **up** when the request succeeds, the status matches
`expected_status` (or is 2xx/3xx), and the optional `keyword` is present. A
single failure does not trigger an alert — the monitor waits for
`failures_before_down` consecutive failures, then emits `site_down`. It returns
to `up` (emitting `site_recovered`) after `successes_before_up` consecutive
successes. State persists to `state_file`, so a restart won't re-alert.
