#!/usr/bin/env bash
# =============================================================================
# SmartSprinkler Validation Cron Wrapper
# =============================================================================
# Runs daily via crontab. Guards against concurrent runs.
# Executes ONLY if more than 6 days have passed since last successful run.
# Execution order: validate_network.py → auto_adjuster.py
#
# To install:
#   chmod +x cron_validator.sh
#   # edit CRON_ROOT below to match your install path
#   (crontab -l 2>/dev/null | grep -v cron_validator.sh; echo "0 6 * * * /full/path/to/cron_validator.sh >> /full/path/to/cron_validator.log 2>&1") | crontab -
#
# Log: data/cron_validator.log
# State: data/validation_state.json
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BAYESIAN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCKFILE="$BAYESIAN_DIR/data/cron_validator.lock"
LOGFILE="$BAYESIAN_DIR/data/cron_validator.log"
STATEFILE="$BAYESIAN_DIR/data/validation_state.json"
REPORTFILE="$BAYESIAN_DIR/validation_report.md"

MIN_INTERVAL_DAYS=6

# ── Pre-flight ────────────────────────────────────────────────────────────────

mkdir -p "$(dirname "$LOCKFILE")" "$(dirname "$LOGFILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOGFILE"
}

# Prevent concurrent runs
if [[ -f "$LOCKFILE" ]]; then
    log "ERROR: Lock file exists ($LOCKFILE). Another instance may be running. Exiting."
    exit 1
fi
trap 'rm -f "$LOCKFILE"' EXIT
echo "$$" > "$LOCKFILE"

log "=== Cron validation started ==="

# ── Check interval ─────────────────────────────────────────────────────────────

days_since_last_run() {
    if [[ ! -f "$STATEFILE" ]]; then
        echo 999
        return
    fi
    local last_run
    last_run=$(python3 -c "import json; d=json.load(open('$STATEFILE')).get('last_successful_run_at',''); print(d if d else '0')")
    if [[ "$last_run" == "0" || -z "$last_run" ]]; then
        echo 999
        return
    fi
    # Parse ISO timestamp and compute days diff
    python3 -c "
import sys
from datetime import datetime, timezone
last = datetime.fromisoformat('$last_run'.replace('Z','+00:00'))
now = datetime.now(timezone.utc)
print((now - last).days)
"
}

days=$(days_since_last_run)
log "Days since last successful run: $days (minimum: $MIN_INTERVAL_DAYS)"

if [[ "$days" -lt "$MIN_INTERVAL_DAYS" ]]; then
    log "Interval not reached. Skipping this run."
    exit 0
fi

# ── Step 1: Run validation ────────────────────────────────────────────────────

log "Step 1: Running validate_network.py ..."

if ! (cd "$BAYESIAN_DIR" && uv run python scripts/validate_network.py >> "$LOGFILE" 2>&1); then
    log "ERROR: validate_network.py failed. Check $LOGFILE for details."
    exit 1
fi

if [[ ! -f "$REPORTFILE" ]]; then
    log "ERROR: Report was not generated at $REPORTFILE"
    exit 1
fi

log "Step 1 complete."

# ── Step 2: Auto-adjust CPT weights ─────────────────────────────────────────

log "Step 2: Running auto_adjuster.py ..."

if ! (cd "$BAYESIAN_DIR" && uv run python scripts/auto_adjuster.py >> "$LOGFILE" 2>&1); then
    log "ERROR: auto_adjuster.py failed. Check $LOGFILE for details."
    exit 1
fi

log "Step 2 complete."

# ── Done ─────────────────────────────────────────────────────────────────────

log "=== Cron validation complete ==="