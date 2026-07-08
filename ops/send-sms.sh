#!/usr/bin/env bash
#
# send-sms.sh — send an SMS via Twilio. Message comes from $1 or stdin.
# Used by the briefing agent to text the daily summary to the owner.
# Reads TWILIO_* + BRIEFING_TO from the environment (ops.env).
#
set -euo pipefail

BODY="${1:-$(cat)}"
: "${TWILIO_ACCOUNT_SID:?set TWILIO_ACCOUNT_SID in ops.env}"
: "${TWILIO_AUTH_TOKEN:?set TWILIO_AUTH_TOKEN in ops.env}"
: "${TWILIO_FROM:?set TWILIO_FROM in ops.env}"
TO="${BRIEFING_TO:-${FIGARO_OWNER_PHONE:-}}"
: "${TO:?set BRIEFING_TO (or FIGARO_OWNER_PHONE) in ops.env}"

# Twilio caps a message at 1600 chars; trim defensively.
BODY="${BODY:0:1500}"

curl -sS -X POST "https://api.twilio.com/2010-04-01/Accounts/${TWILIO_ACCOUNT_SID}/Messages.json" \
  --data-urlencode "From=${TWILIO_FROM}" \
  --data-urlencode "To=${TO}" \
  --data-urlencode "Body=${BODY}" \
  -u "${TWILIO_ACCOUNT_SID}:${TWILIO_AUTH_TOKEN}" \
  -o /dev/null -w "sent (%{http_code})\n"
