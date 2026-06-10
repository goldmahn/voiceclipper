#!/usr/bin/env bash
# Run a command (typically voiceclipper) while logging memory/CPU snapshots.
#
# Usage:
#   ./scripts/run-monitored.sh --log path/to/resource.log -- command [args...]
#   ./scripts/run-monitored.sh --notify --log path/to/resource.log -- voiceclipper clip ...
#
# Options:
#   --log PATH       Resource log file (required)
#   --interval SEC   Sample interval (default: 5)
#   --notify         macOS Notification Center alert when the command finishes
#   --               End of options; remainder is the command to run

set -euo pipefail

INTERVAL=5
LOG_FILE=""
NOTIFY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --log)
      LOG_FILE="$2"
      shift 2
      ;;
    --interval)
      INTERVAL="$2"
      shift 2
      ;;
    --notify)
      NOTIFY=1
      shift
      ;;
    --)
      shift
      break
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$LOG_FILE" ]]; then
  echo "error: --log PATH is required" >&2
  exit 2
fi

if [[ $# -lt 1 ]]; then
  echo "error: no command provided after --" >&2
  exit 2
fi

mkdir -p "$(dirname "$LOG_FILE")"

notify() {
  local title="$1"
  local message="$2"
  osascript -e "display notification \"$message\" with title \"$title\" sound name \"Glass\"" 2>/dev/null || true
}

log_snapshot() {
  {
    echo "=== $(date -Iseconds) ==="
    memory_pressure 2>/dev/null | head -6 || echo "memory_pressure: unavailable"
    vm_stat 2>/dev/null | head -8 || true
    ps -ax -o pid,rss,comm 2>/dev/null | awk 'NR==1 || /voiceclipper|Python|python|ffmpeg|whisper/i' || true
    echo ""
  } >> "$LOG_FILE"
}

monitor_loop() {
  while kill -0 "$CMD_PID" 2>/dev/null; do
    log_snapshot
    sleep "$INTERVAL"
  done
}

START_EPOCH=$(date +%s)
{
  echo "voiceclipper monitored run"
  echo "started: $(date -Iseconds)"
  echo "command: $*"
  echo "interval: ${INTERVAL}s"
  echo ""
} >> "$LOG_FILE"

log_snapshot
"$@" &
CMD_PID=$!
monitor_loop &
MONITOR_PID=$!

wait "$CMD_PID"
EXIT_CODE=$?
kill "$MONITOR_PID" 2>/dev/null || true
wait "$MONITOR_PID" 2>/dev/null || true

END_EPOCH=$(date +%s)
ELAPSED=$((END_EPOCH - START_EPOCH))

{
  echo "=== summary ==="
  echo "finished: $(date -Iseconds)"
  echo "elapsed_seconds: $ELAPSED"
  echo "exit_code: $EXIT_CODE"
  memory_pressure 2>/dev/null | head -6 || true
  echo ""
} >> "$LOG_FILE"

if [[ "$NOTIFY" -eq 1 ]]; then
  if [[ "$EXIT_CODE" -eq 0 ]]; then
    notify "Voiceclipper" "Finished OK in ${ELAPSED}s. Log: ${LOG_FILE}"
  else
    notify "Voiceclipper" "Failed (exit ${EXIT_CODE}) after ${ELAPSED}s. Log: ${LOG_FILE}"
  fi
fi

echo "resource log: $LOG_FILE"
echo "exit code: $EXIT_CODE"
exit "$EXIT_CODE"
