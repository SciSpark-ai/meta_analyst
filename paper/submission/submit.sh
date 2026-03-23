#!/usr/bin/env bash
set -euo pipefail

# clawRxiv submission script for Meta-Analyst research note
# Usage: ./submit.sh <API_KEY>

API_BASE="http://18.118.210.52"

# --- Argument check ---
if [ $# -lt 1 ]; then
  echo "Usage: $0 <API_KEY>"
  echo "  Obtain a key: curl -s -X POST ${API_BASE}/api/auth/register -H 'Content-Type: application/json' -d '{\"claw_name\":\"meta-analyst\"}'"
  exit 1
fi

API_KEY="$1"

# --- Dependency check ---
if ! command -v jq &>/dev/null; then
  echo "Error: jq is required but not installed."
  echo "  Install with: brew install jq  (macOS) or apt-get install jq  (Linux)"
  exit 1
fi

# --- Resolve paths relative to this script ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESEARCH_NOTE="${SCRIPT_DIR}/../research_note.md"
SKILL_FILE="${SCRIPT_DIR}/../../skills/meta-analyst/SKILL.md"

if [ ! -f "$RESEARCH_NOTE" ]; then
  echo "Error: Research note not found at ${RESEARCH_NOTE}"
  exit 1
fi

if [ ! -f "$SKILL_FILE" ]; then
  echo "Error: Skill file not found at ${SKILL_FILE}"
  exit 1
fi

# --- Read content ---
CONTENT="$(cat "$RESEARCH_NOTE")"
SKILL_CONTENT="$(cat "$SKILL_FILE")"

# --- Extract abstract (text between ## Abstract and next ## heading) ---
ABSTRACT="$(sed -n '/^## Abstract$/,/^## /{/^## Abstract$/d;/^## /d;p;}' "$RESEARCH_NOTE" | sed '/^$/N;/^\n$/d' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' | tr '\n' ' ' | sed 's/  */ /g' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

if [ -z "$ABSTRACT" ]; then
  echo "Error: Could not extract abstract from research note."
  echo "  Ensure the note contains an '## Abstract' section."
  exit 1
fi

TITLE="Meta-Analyst: Executable Clinical Meta-Analysis as an Agent Skill"

# --- Build JSON payload ---
PAYLOAD="$(jq -n \
  --arg title "$TITLE" \
  --arg abstract "$ABSTRACT" \
  --arg content "$CONTENT" \
  --arg skill_md "$SKILL_CONTENT" \
  '{
    title: $title,
    abstract: $abstract,
    content: $content,
    tags: ["meta-analysis", "clinical-research", "agent-skill", "cochrane", "grade"],
    human_names: ["Tong Shan", "Lei Li"],
    skill_md: $skill_md
  }'
)"

# --- Submit ---
echo "Submitting to clawRxiv..."
RESPONSE="$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/api/posts" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")"

HTTP_CODE="$(echo "$RESPONSE" | tail -1)"
BODY="$(echo "$RESPONSE" | sed '$d')"

if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
  POST_ID="$(echo "$BODY" | jq -r '.id // .post_id // empty')"
  echo "Submission successful (HTTP ${HTTP_CODE})."
  if [ -n "$POST_ID" ]; then
    echo "Verification URL: ${API_BASE}/api/posts/${POST_ID}"
  fi
  echo "$BODY" | jq .
else
  echo "Submission failed (HTTP ${HTTP_CODE})."
  echo "$BODY"
  exit 1
fi
