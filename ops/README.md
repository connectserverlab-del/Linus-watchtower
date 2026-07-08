# Lumina Ops — VPS agent toolkit

Runs Claude agents on the VPS via the `claude` CLI headless, on systemd timers.
Two jobs: **host the overnight pipeline** (research → implement → burn-down) and
an **ops/monitor agent** that keeps the always-on services healthy.

Nothing here holds secrets — auth and config live in `ops.env` (git-ignored).

## Agents & schedule

| Agent | Prompt | Timer (ET*) | Does |
| --- | --- | --- | --- |
| **ops-monitor** | `prompts/ops-monitor.md` | every 30 min | Health of `figaro`/`linus-uptime`, disk, uptime state; restart, file Jira, small fixes |
| **research** | `prompts/research.md` | 12a / 4a / 8a | Research + file `auto-agent` backlog, write research notes |
| **implement** | `prompts/implement.md` | 9a | Build **tonight's freshest** research into draft PRs (last 2h) |
| **burndown** | `prompts/burndown.md` | 2a / 6a / 10a | Pick a ready task, implement, open a draft PR |
| **briefing** | `prompts/briefing.md` | 10a | **Texts you** (Twilio) a summary of overnight updates, research, PRs to review, and uptime |

\* The timers use ET and auto-handle DST **if the box timezone is set**:
`sudo timedatectl set-timezone America/New_York`. This mirrors the cloud Routines
so you can run both while validating, then retire the cloud pair.

## Prerequisites (one-time, on the box)

1. **A user to run as** (examples assume `ops`): `sudo useradd -m -r -s /bin/bash ops`.
2. **Claude auth** — either set `ANTHROPIC_API_KEY` in `ops.env` (pay-per-use API,
   separate from a Claude subscription), or `sudo -u ops claude login` once so
   `~ops/.claude` holds the session.
3. **MCP connectors** for the `ops` user's `claude` config — **Jira** (Atlassian)
   and **GitHub**, with their tokens (Jira API token; a GitHub token or App).
   Without these the agents can still run but will skip Jira/PR steps.
4. **Repos cloned** under `OPS_WORKDIR` (e.g. `/opt/lumina`): `tessera`, `argus`,
   `vellum`, `research`, and clone this repo to `/opt/linus-watchtower`.
5. **Git push auth** for the `ops` user (a GitHub token via credential helper or
   an SSH deploy key per repo) so agents can push branches.
6. Confirm the CLI's full-auto flag: `claude --help` → set `CLAUDE_ARGS` in
   `ops.env` (e.g. `--permission-mode bypassPermissions`).
7. **For the briefing SMS:** set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`,
   `TWILIO_FROM`, and `BRIEFING_TO` (your phone) in `ops.env`. Reuses the same
   Twilio number as Figaro. (US texting needs A2P 10DLC — same as Figaro.)

## Install

```bash
sudo git clone https://github.com/connectserverlab-del/linus-watchtower /opt/linus-watchtower
cd /opt/linus-watchtower/ops
cp ops.env.example ops.env   # fill it in
sudo chown -R ops:ops /opt/linus-watchtower /opt/lumina

# Install the units
sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lumina-ops-monitor.timer \
                            lumina-research.timer \
                            lumina-implement.timer \
                            lumina-burndown.timer \
                            lumina-briefing.timer

systemctl list-timers 'lumina-*'      # verify schedule
journalctl -u lumina-ops-monitor -f   # watch a run
```

Test one agent by hand before enabling the timers:

```bash
sudo -u ops OPS_ENV_FILE=/opt/linus-watchtower/ops/ops.env \
     /opt/linus-watchtower/ops/run-agent.sh ops-monitor
```

## Safety

- Agents open **draft PRs only** and never merge or push to `main` — same rules
  as the cloud Routines; you review and merge.
- All agents use the **disjoint-file / fresh-branch** discipline so the
  implement + burn-down agents don't collide. Stagger or trim timers if you see
  contention (e.g. drop the 10a burn-down so 9–11a is implement-only).
- The ops-monitor is conservative: it restarts a service or removes clearly-safe
  rotated logs, nothing more.
- **Cost** scales with agent count (each run is a Claude session). Watch usage;
  the ops-monitor's summaries tell you if an agent is churning without output.

## Files

`run-agent.sh` (shared runner), `prompts/*.md` (one per agent), `systemd/*`
(service + timer per agent), `ops.env.example`.
