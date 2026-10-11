#!/usr/bin/env python3
"""init_csvs.py -- create any missing data CSV with just its header row.

Headers come from the scripts that write the files, so they can't drift.
Existing files are never touched.
"""
import csv
import os
import sys

DUAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DUAL)

import pi_link  # noqa: E402

# capture_gpr imports cv2/numpy at module level; read its header without them.
ns = {}
src = open(os.path.join(DUAL, "capture_gpr.py")).read()
start = src.index("CSV_HEADER = [")
exec(src[start:src.index("]", start) + 1], ns)

files = [
    (os.path.join(DUAL, "growth_dataset.csv"), ns["CSV_HEADER"]),
    (pi_link.SM_CSV, pi_link.SM_HEADER),
    (pi_link.EVT_CSV, pi_link.EVT_HEADER),
    (pi_link.ERR_CSV, pi_link.ERR_HEADER),
]
for path, header in files:
    if os.path.exists(path):
        print(f"  kept     {path}")
        continue
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        csv.writer(f).writerow(header)
    print(f"  created  {path}")
