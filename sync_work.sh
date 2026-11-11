#!/usr/bin/env bash
# ==============================================================================
# sync_work.sh -- One-command sync, handoff updater, and git push
# ==============================================================================
# Usage:
#   ./sync_work.sh manuscript ["commit message"]   Update MANUSCRIPT.md, recompile, & push
#   ./sync_work.sh hardware   ["commit message"]   Update HANDOFF.md with Run 2 status & push
#   ./sync_work.sh auto       ["commit message"]   Auto-detect changes, update, & push
# ==============================================================================
set -euo pipefail

cd "$(dirname "$0")"

exec python3 tools/sync_work.py "$@"
