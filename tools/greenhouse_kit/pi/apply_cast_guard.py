#!/usr/bin/env python3
"""apply_cast_guard.py -- OPTIONAL: make the noon capture retry blue (overcast) frames.

Runs ON THE PI. Adds one guard to Dual_Archi/capture_gpr.py, right after the
existing weak-alignment guard and written the same way:

    if the frame's blue/red ratio (median of all pixels) is above 1.25,
    do not write the day; the next 10-minute retry tries again.
    The 12:50 retry writes anyway, so a day is never lost to the guard.

Normal frames measure 0.95-1.14; the bad ones were D04 1.34, D05 1.53,
D12 retake 1.49 and D19 1.84. Nothing else in the capture changes.

    python3 ~/fixkit/apply_cast_guard.py           # show what would change
    python3 ~/fixkit/apply_cast_guard.py --apply   # back up and patch
    python3 ~/fixkit/apply_cast_guard.py --undo    # restore the backup
"""
import argparse
import os
import shutil
import sys

TARGET = os.path.expanduser("~/THESIS/Dual_Archi/capture_gpr.py")
BACKUP = TARGET + ".before_cast_guard"
ANCHOR = ('            sys.exit(f"[capture_gpr] camera alignment too weak (confidence {aconf:.2f}) -- "\n'
          '                     f"day {d} not written; the next retry will try again")\n')
GUARD = '''
    # Colour-cast guard (fixkit, Nov 2026). Overcast light under the locked daylight
    # white balance turns the frame blue; leaf pixels then fall under SAT_MIN and
    # GPR reads low (D19: blue/red 1.84, GPR about half). Leave such a frame to the
    # next 10-min retry. The last retry (12:50) writes anyway; the value is printed
    # to cron.log either way.
    _med = np.median(frame.reshape(-1, 3), axis=0)
    _cast = float(_med[0]) / max(float(_med[2]), 1.0)
    print(f"[capture_gpr] colour cast blue/red = {_cast:.2f} (normal about 1.0)")
    if (_cast > 1.25 and not args.no_write and not args.test_image
            and not args.force and datetime.now().minute < 50):
        sys.exit(f"[capture_gpr] blue colour cast {_cast:.2f} -- day {d} not written; "
                 f"the next retry will try again")
'''
MARK = "Colour-cast guard (fixkit"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--undo", action="store_true")
    a = ap.parse_args()
    if a.undo:
        if not os.path.exists(BACKUP):
            sys.exit("no backup found; nothing to undo")
        shutil.copy2(BACKUP, TARGET)
        print(f"restored {TARGET} from {BACKUP}")
        return
    raw = open(TARGET, "rb").read().decode("utf-8")
    crlf = "\r\n" in raw
    src = raw.replace("\r\n", "\n")
    if MARK in src:
        print("guard already in capture_gpr.py; nothing to do")
        return
    if src.count(ANCHOR) != 1:
        sys.exit("could not find the alignment guard in capture_gpr.py; NOT patching "
                 "(the file differs from the version this was written for)")
    new = src.replace(ANCHOR, ANCHOR + GUARD)
    if not a.apply:
        print("Would add after the alignment guard:\n" + GUARD)
        print("(preview only; run with --apply to patch)")
        return
    compile(new, TARGET, "exec")          # refuse to write a file that would not run
    shutil.copy2(TARGET, BACKUP)
    out = new.replace("\n", "\r\n") if crlf else new
    open(TARGET, "wb").write(out.encode("utf-8"))
    print(f"patched {TARGET}\nbackup: {BACKUP}\nundo:   python3 ~/fixkit/apply_cast_guard.py --undo")


if __name__ == "__main__":
    main()
