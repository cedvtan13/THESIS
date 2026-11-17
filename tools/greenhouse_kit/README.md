# Greenhouse kit: how to work with the Pi until harvest

For **Cedric, Rey and Kent**. Written Nov 17, 2026, after the D18 and D20 incidents.

## The one rule

**Never run git on the Pi.**
- On Nov 15 a `git pull` on the Pi wiped the D18 rows and reset the sowing date.
- On Nov 17 a pull hit merge conflicts inside the live CSVs.

Git merges on the Pi are now blocked (`protect_data.sh`).

| What | How it travels |
|---|---|
| Data | Pi → laptop (`pull`) → GitHub, from the laptop |
| Code | laptop → Pi by `scp` only (the kit does it) |

## Never between 11:45 and 12:55

That is the noon capture window (tries at 12:00 to 12:50). Don't run anything on the Pi then, and don't touch the camera.

## Commands

The laptop must be on the Pi's hotspot. The Pi password is for user `crk`.

| Job | Windows (`windows\`), double-click | Mac / Linux (`mac_linux/`) |
|---|---|---|
| Find the Pi | `find_pi.bat` | `ping groupb.local` |
| Daily health check (read-only) | `check_pi.bat` | `./kit.sh check` |
| Bring all data and frames to the laptop | `pull_from_pi.bat` | `./kit.sh pull` |
| Install or refresh the kit on the Pi | `send_kit_to_pi.bat` | `./kit.sh send` |
| Git guard, light_log off, field notes | `tomorrow_fixes.bat` | `./kit.sh fixes` |
| Resolve D20 duplicate rows, limit catch_up | `fix_d20.bat` | `./kit.sh fix-d20` |
| Mask comparison (read-only) | `run_mask_compare.bat` | `./kit.sh mask` |
| Blue-frame retry guard (**already applied Nov 17**) | `apply_cast_guard.bat` | `ssh crk@groupb.local "python3 ~/fixkit/apply_cast_guard.py"` |

**If the Pi isn't found by name,** find its IP in the hotspot's connected-devices list ("groupb"):
- Windows: `check_pi.bat 172.20.10.3`
- Mac: `PI_HOST=172.20.10.3 ./kit.sh check`

Pulls go to `pi_pulls/<date_time>/` **next to** the THESIS folder as a staging area; raw noon frames (`~3 MB` each) are then copied into `THESIS/DATA/agrisentry_data/frames/` so they are synced to GitHub.

## After a pull: getting it into GitHub (from the laptop)

1. Copy the newer data files and raw noon frames from the pull into the repo:
   - `pi_pulls/<x>/thesis/` → `THESIS/Dual_Archi/`
   - `pi_pulls/<x>/agrisentry_data/*.csv` → `THESIS/DATA/agrisentry_data/`
   - `pi_pulls/<x>/agrisentry_data/frames/` → `THESIS/DATA/agrisentry_data/frames/` (all `D*_*.png` raw noon frames and `overlay/`)
2. Add a dated entry to `DATA/` (what came in) and to `DATA/2026-11-17-run2-event-log.md` (anything that happened).
3. Update the READ FIRST section of `HANDOFF.md`.
4. `git pull`, then `git add <those files>`, `git commit -m "..."`, `git push`.

Kent works through steps 1 to 3 with Claude.

## Every manual action

Add a line to the Pi's `~/thesis/field_log.csv` in this format:

```
2026-11-18,21,P-04,"what you did, at what time, who"
```

Then add the same event to the event log at the next update.

## Don't, until harvest

- any git command on the Pi;
- running `capture_gpr.py` by hand, especially with `--force` (it **appends** a duplicate day);
- `agrisentry.sh start` (it turns the hourly camera job back on, which crashes the Pi at :30);
- re-flashing the ESP32;
- moving pots or replanting.
