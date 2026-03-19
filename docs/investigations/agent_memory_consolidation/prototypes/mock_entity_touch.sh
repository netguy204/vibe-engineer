#!/bin/bash
# Mock implementation of `ve entity touch <memory_id>`
# Logs touches to a file for experiment analysis
LOGFILE="$(dirname "$0")/touch_log.jsonl"
MEMORY_ID="$1"
REASON="$2"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ -z "$MEMORY_ID" ]; then
    echo "Usage: ve entity touch <memory_id> [reason]"
    exit 1
fi

echo "{\"timestamp\": \"$TIMESTAMP\", \"memory_id\": \"$MEMORY_ID\", \"reason\": \"$REASON\"}" >> "$LOGFILE"
echo "Touched memory: $MEMORY_ID"
