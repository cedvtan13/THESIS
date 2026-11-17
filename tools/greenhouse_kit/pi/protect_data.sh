#!/usr/bin/env bash
# protect_data.sh -- stop git and the hourly camera job from hurting the run.
# Runs ON THE PI. Safe to run more than once. Undo with:  bash protect_data.sh undo
#
# 1. GIT GUARD. The Pi's live data files sit inside the git folder ~/THESIS.
#    On Nov 15 a git pull/merge on the Pi put back the repo's old growth_dataset.csv
#    (losing the D18 rows written at 12:00) and an old sowing_date.txt (2026-10-06),
#    so capture_gpr.py refused to write from Nov 15 12:20 until Nov 16 ~12:45.
#    This marks every live data file "skip-worktree": git will no longer overwrite
#    them; a pull that would touch them stops with an error instead.
#    Also installs a git hook that refuses `git pull`/merge on the Pi entirely.
#    Code changes reach the Pi with sync_pi.sh push / scp, never with git pull.
# 2. CAMERA CRASHES. Most Pi-only crashes since Nov 12 happen at :30, when the
#    hourly light_log.py turns the camera on. That job is diagnostic only; this
#    comments it out (the noon capture, glare check and throttle log stay on).
set -uo pipefail
REPO="$HOME/THESIS"
DUAL="$REPO/Dual_Archi"
FILES=(growth_dataset.csv align_log.csv exposure_log.csv glare_log.csv light_log.csv
       field_log.csv sowing_date.txt pot_rois.json align_ref.png time_test_log.csv)

if [[ ${1:-} == undo ]]; then
  cd "$REPO" && for f in "${FILES[@]}"; do git update-index --no-skip-worktree "Dual_Archi/$f" 2>/dev/null; done
  rm -f "$REPO/.git/hooks/pre-merge-commit" "$REPO/.git/hooks/post-checkout.fixkit"
  crontab -l | sed 's|^#FIXKIT-OFF# ||' | crontab -
  echo "undone: git guard removed, light_log cron restored"; exit 0
fi

echo "== 1. git guard"
if [[ -d $REPO/.git ]]; then
  cd "$REPO"
  for f in "${FILES[@]}"; do
    if git ls-files --error-unmatch "Dual_Archi/$f" >/dev/null 2>&1; then
      git update-index --skip-worktree "Dual_Archi/$f" && echo "   protected Dual_Archi/$f"
    fi
  done
  cat > .git/hooks/pre-merge-commit <<'HOOK'
#!/bin/sh
echo "BLOCKED by fixkit: do not merge/pull on the Pi during the run (live data lives here)."
echo "Send code with sync_pi.sh push or scp instead. Undo: bash ~/fixkit/protect_data.sh undo"
exit 1
HOOK
  chmod +x .git/hooks/pre-merge-commit
  echo "   merge hook installed"
  echo "   current git status of data files:"
  git ls-files -v Dual_Archi | grep '^S' | sed 's/^/     /'
else
  echo "   no git folder at $REPO (nothing to protect)"
fi

echo "== 2. hourly light_log camera job"
if crontab -l 2>/dev/null | grep -q '^[^#].*light_log.py'; then
  crontab -l | sed 's|^\(.*light_log.py.*\)$|#FIXKIT-OFF# \1|' | crontab -
  echo "   light_log cron turned OFF (undo: bash ~/fixkit/protect_data.sh undo)"
else
  echo "   light_log cron already off"
fi

echo "== 3. sowing date"
SD=$(cat "$DUAL/sowing_date.txt" 2>/dev/null | tr -d '\r\n ')
if [[ $SD == 2026-10-29 ]]; then echo "   OK ($SD)"; else
  echo "   WRONG ($SD) -> fixing to 2026-10-29"; printf '2026-10-29\n' > "$DUAL/sowing_date.txt"; fi
echo "done."
