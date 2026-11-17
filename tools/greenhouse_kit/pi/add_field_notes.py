#!/usr/bin/env python3
"""add_field_notes.py -- add pending notes to the Pi's field_log.csv.
Safe to run more than once: a note is skipped if its key text is already there.
Backs up the file first."""
import os
import shutil

FLOG = os.path.join(os.path.expanduser("~"), "thesis", "field_log.csv")
# (key text that proves the note is already there, full CSV line)
NOTES = [
    ("stray greenery",
     '2026-11-12,15,P-09,"D15 P-09 cell_gpr is inflated: stray greenery from outside plants '
     'intruded into the P-09 area (recorded in field_log.txt on Nov 12). Row kept as measured."'),
    ("P-01 SOIL WET",
     '2026-11-16,19,P-01,"P-01 SOIL WET to the touch (Kent, Nov 16 afternoon); no dripping from its hose. '
     'Its ~90-95 % readings since Nov 8 are real waterlogging after the seven 100 mL doses of Nov 7-8, '
     'not a probe fault."'),
    ("P-03 SEEDLING DEAD",
     '2026-11-16,19,P-03,"P-03 SEEDLING DEAD (Kent, Nov 16 afternoon). cell_gpr 0.00 on D17-D19. '
     'Not replanted. P-03 is in the planned sensitivity set (P-01, P-03, P-06)."'),
    ("P-04 seedling alive",
     '2026-11-16,19,P-04,"P-04 seedling alive and looks okay (Kent, Nov 16 afternoon); its low D17 GPR '
     '(0.01 %) was not a dead plant."'),
    ("D18 CAUSE CORRECTED",
     '2026-11-16,18,ALL,"D18 CAUSE CORRECTED: the D18 rows WERE written at 12:00 on Nov 15 (cron.log: '
     'day 18 already in the CSV at 12:10). Most likely a git pull/merge on the Pi around 12:16 (repo commit 2b909b9, Resolve file deletion conflicts) then put back the '
     'repo copies of growth_dataset.csv (without D18) and sowing_date.txt (2026-10-06), so the rows were '
     'lost and every capture from Nov 15 12:20 to Nov 16 12:40 refused (D=41/42 outside the cycle). '
     'Rows re-measured from the saved frame on Nov 16 16:47 (recover_day.py). Data files now protected '
     'from git (protect_data.sh)."'),
    ("D19 BLUE COLOUR CAST",
     '2026-11-16,19,ALL,"D19 BLUE COLOUR CAST: captured 12:47 (late, after the sowing-date fix and a '
     'Pi-only crash at 12:16) under overcast light; frame blue/red 1.84 vs about 1.0 normally, so '
     'leaf pixels dropped out and GPR read about half of D18. Row kept as measured; flag R."'),
]
if not os.path.exists(FLOG):
    raise SystemExit(f"{FLOG} not found")
text = open(FLOG, errors="replace").read()
todo = [line for key, line in NOTES if key not in text]
if not todo:
    print("field log already has all notes; nothing to do")
else:
    shutil.copy2(FLOG, FLOG + ".before_add_notes")
    with open(FLOG, "a", newline="") as f:
        nl = "\r\n" if "\r\n" in text else "\n"
        if not text.endswith("\n"):
            f.write(nl)
        for line in todo:
            f.write(line + nl)
            print("added:", line[:100], "...")
