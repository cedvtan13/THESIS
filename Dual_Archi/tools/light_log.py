#!/usr/bin/env python3
"""
light_log.py -- hourly light reading from the GPR camera (no extra hardware).

The camera runs with locked gain and is brightness-matched to the same target as
the noon capture. The exposure it needs is therefore a light meter: a darker sky
needs a longer exposure.

    light_index = (mean_v / target_v) * (1000 / exposure_ms)

The index is relative, not lux: 100 = the brightness of a 10 ms exposure on
target. It is only comparable between readings from this camera at this mount.
A reading at the 1 ms floor that is still too bright is marked "bright_clip",
and one at the 100 ms ceiling that is still too dark is marked "dark_clip".

Cron (installed by agrisentry.sh start). Skips 12:xx so it never fights the
noon capture for the camera:
    30 6-11,13-18 * * *  python3 ~/THESIS/Dual_Archi/tools/light_log.py

Output: ~/thesis/light_log.csv
    timestamp, day, exposure_us, mean_v, target_v, light_index, note
"""
import csv
import os
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import capture_gpr as cg  # noqa: E402

OUT = os.path.join(cg.BASE, "light_log.csv")
HEADER = ["timestamp", "day", "exposure_us", "mean_v", "target_v", "light_index", "note"]


def day_or_blank():
    try:
        d = (datetime.now().date() - datetime.strptime(cg.sowing_date(), "%Y-%m-%d").date()).days + 1
        return d if 1 <= d <= cg.CYCLE_DAYS else ""
    except ValueError:
        return ""


def main():
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    note = ""
    try:
        cam = cg.open_locked_camera()
        time.sleep(2)
        cg._match_brightness(cam, cam.capture_array())
        cam.stop()
        cam.close()
        exp = cg.LAST_EXPOSURE["exposure_us"]
        v = cg.LAST_EXPOSURE["mean_v"]
        if exp <= cg.EXPOSURE_MIN_US and v > 1.05 * cg.TARGET_MEAN_V:
            note = "bright_clip"
        elif exp >= cg.EXPOSURE_MAX_US and v < 0.95 * cg.TARGET_MEAN_V:
            note = "dark_clip"
        idx = f"{(v / cg.TARGET_MEAN_V) * (1000.0 / (exp / 1000.0)):.1f}"
    except Exception as e:          # camera busy, not connected, ...
        exp, v, idx, note = "", "", "", f"error: {e}"[:120]

    new = not os.path.exists(OUT)
    with open(OUT, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(HEADER)
        w.writerow([stamp, day_or_blank(), exp, v, cg.TARGET_MEAN_V, idx, note])
    print(f"[light_log] {stamp} exposure={exp} us mean_v={v} index={idx} {note}")


if __name__ == "__main__":
    main()
