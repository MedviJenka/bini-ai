#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${1:-$SCRIPT_DIR/../../.env}"
REPLACE_EXISTING="${REPLACE_EXISTING:-false}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE" >&2
  exit 1
fi

create_secret() {
  local key="$1"
  local value="$2"

  if docker secret inspect "$key" >/dev/null 2>&1; then
    if [[ "$REPLACE_EXISTING" == "true" ]]; then
      docker secret rm "$key" >/dev/null
    else
      echo "Skipping existing secret: $key"
      return 0
    fi
  fi

  printf '%s' "$value" | docker secret create "$key" - >/dev/null
  echo "Created secret: $key"
}

while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
  line="${raw_line%$'\r'}"

  if [[ -z "${line//[[:space:]]/}" || "$line" =~ ^[[:space:]]*# ]]; then
    continue
  fi

  if [[ "$line" != *"="* ]]; then
    echo "Skipping invalid line: $line" >&2
    continue
  fi

  key="${line%%=*}"
  value="${line#*=}"
  key="${key#export }"
  key="${key##[[:space:]]}"
  key="${key%%[[:space:]]}"

  if [[ -z "$key" ]]; then
    echo "Skipping line with empty key" >&2
    continue
  fi

  if [[ -z "$value" ]]; then
    echo "Skipping empty secret value: $key"
    continue
  fi

  create_secret "$key" "$value"
done < "$ENV_FILE"
