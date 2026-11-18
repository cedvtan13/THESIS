#!/usr/bin/env python3
"""daily_check.py -- read-only health report for the Pechay greenhouse run.

Runs ON THE PI. Needs no internet and changes nothing. Checks:
  * every day from D1 to today has 9 rows in growth_dataset.csv
  * a missing day whose noon frame exists (recoverable with recover_day.py)
  * today's capture: time, exposure, brightness and alignment confidence
  * GPR drops that hit almost every pot at once (light, not plants)
  * pots whose GPR has been 0 for 2 or more days (check the seedling)
  * pots far outside their soil moisture band for 3 or more days
  * whether the soil moisture logger (pi_link) is still writing
  * irrigation doses missing from the log (gaps in event_count)
  * error and power events in the last 24 hours
  * free disk space and the latest backup

    python3 ~/fixkit/daily_check.py            # print the report, save a copy
    python3 ~/fixkit/daily_check.py --no-save  # print only

The report is saved to ~/fixkit/reports/check_YYYY-MM-DD_HHMM.txt.
"""
import argparse
import collections
import csv
import glob
import os
import shutil
import sys
from datetime import datetime, timedelta

HOME = os.path.expanduser("~")
DUAL = os.path.join(HOME, "THESIS", "Dual_Archi")
sys.path.insert(0, DUAL)
try:
    import capture_gpr as cg  # same paths and sowing date as the live pipeline
    BASE, OUT_CSV, FRAME_DIR = cg.BASE, cg.OUT_CSV, cg.FRAME_DIR
except Exception as e:  # still useful without OpenCV
    print(f"(capture_gpr not importable: {e}; using default paths)")
    cg = None
    BASE = os.path.join(HOME, "thesis")
    OUT_CSV = os.path.join(BASE, "growth_dataset.csv")
    FRAME_DIR = os.path.join(HOME, "agrisentry_data", "frames")
DATA = os.path.join(HOME, "agrisentry_data")
KIT = os.path.join(HOME, "fixkit")
BACKUPS = os.path.join(HOME, "backups")

POTS = [f"P-{i:02d}" for i in range(1, 10)]
GROUP = {"P-01": "Low", "P-02": "Low", "P-03": "Low",
         "P-04": "Medium", "P-05": "Medium", "P-06": "Medium",
         "P-07": "High", "P-08": "High", "P-09": "High"}
BAND = {"Low": (30, 40), "Medium": (50, 60), "High": (70, 80)}
BANDS_ON_DAY = 8
RUN_SOWING = "2026-10-29"
CAST_MAX = 1.25   # blue/red of the frame median; normal frames are about 0.95-1.10

out_lines = []


def say(s=""):
    print(s)
    out_lines.append(s)


def read_csv(path):
    if not os.path.exists(path):
        return None, []
    with open(path, newline="", errors="replace") as f:
        rd = csv.DictReader(f)
        return rd.fieldnames, [r for r in rd]


def fnum(x):
    try:
        v = float(x)
        return None if v != v else v  # NaN -> None
    except (TypeError, ValueError):
        return None


def sowing():
    p = os.path.join(BASE, "sowing_date.txt")
    if os.path.exists(p):
        return datetime.strptime(open(p).read().strip(), "%Y-%m-%d").date()
    return datetime(2026, 10, 29).date()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args()

    now = datetime.now()
    sown = sowing()
    today = (now.date() - sown).days + 1
    capture_done_window = now.hour > 12 or (now.hour == 12 and now.minute >= 55)
    last_due = today if capture_done_window else today - 1
    say(f"Pechay Run 2 daily check  {now:%Y-%m-%d %H:%M}   sowing {sown}   today D{today}")
    say("=" * 72)
    problems = []
    if str(sown) != RUN_SOWING:
        say(f"!! CRITICAL: sowing_date.txt says {sown}, the final run was sown {RUN_SOWING}.")
        say("   capture_gpr.py will REFUSE to write until this is fixed. Fix with:")
        say(f"   echo {RUN_SOWING} > {os.path.join(BASE, 'sowing_date.txt')}")
        say("   (This happened on Nov 15: a git pull on the Pi put back an old file.)")
        problems.append("WRONG SOWING DATE")

    # ---------------------------------------------------------- dataset rows
    _, rows = read_csv(OUT_CSV)
    by_day = collections.defaultdict(list)
    for r in rows:
        try:
            by_day[int(r["day"])].append(r)
        except (KeyError, ValueError):
            pass
    frames = {}
    for p in glob.glob(os.path.join(FRAME_DIR, "D*_*.png")):
        try:
            frames[int(os.path.basename(p)[1:3])] = p
        except ValueError:
            pass
    say(f"\n[1] Dataset rows ({OUT_CSV})")
    missing, wrong = [], []
    for d in range(1, last_due + 1):
        n = len(by_day.get(d, []))
        if n == 0:
            missing.append(d)
        elif n != 9:
            wrong.append((d, n))
    known_lost = {2, 3}  # no capture was made (power outage), documented
    for d in missing:
        if d in known_lost:
            continue
        if d in frames:
            say(f"  MISSING D{d}: frame exists ({os.path.basename(frames[d])}) -> RECOVERABLE:")
            say(f"      python3 ~/fixkit/recover_day.py --day {d}          (preview)")
            say(f"      python3 ~/fixkit/recover_day.py --day {d} --write  (add the rows)")
        else:
            say(f"  MISSING D{d}: no frame either -> record it in the field log as missed")
        problems.append(f"D{d} has no rows")
    for d, n in wrong:
        say(f"  D{d} has {n} rows instead of 9")
        problems.append(f"D{d} has {n} rows")
    nan_days = sorted({int(r['day']) for r in rows if fnum(r.get('sm_pct')) is None})
    if nan_days:
        say(f"  rows with no soil moisture on days: {nan_days}")
    if not missing and not wrong:
        say(f"  OK: D1..D{last_due} all present (D2, D3 known lost)" if last_due >= 1 else "  OK")
    elif set(missing) <= known_lost and not wrong:
        say(f"  OK: D1..D{last_due} present apart from D2, D3 (known lost)")

    # ---------------------------------------------------------- today's capture
    say("\n[2] Latest capture")
    _, exp = read_csv(os.path.join(BASE, "exposure_log.csv"))
    _, aln = read_csv(os.path.join(BASE, "align_log.csv"))
    if exp:
        e = exp[-1]
        us, mv = fnum(e.get("exposure_us")), fnum(e.get("mean_v"))
        say(f"  D{e.get('day')} at {e.get('timestamp')}: exposure {us:.0f} us, mean V {mv:.1f} (target 73)")
        if us and us > 10000:
            say("  WARN: exposure over 10 ms -> dim light; GPR of this day will read LOW")
            problems.append(f"D{e.get('day')} captured in dim light")
        if mv and mv < 71:
            say("  WARN: brightness below 71 -> camera could not reach the target")
        ts = e.get("timestamp", "")
        if ts[-5:] > "12:15":
            say("  NOTE: capture later than 12:15 -> earlier tries failed; see Dual_Archi/cron.log")
    latest = sorted(frames.items())[-1][1] if frames else None
    if latest:
        try:
            import cv2
            import numpy as np
            im = cv2.imread(latest)
            med = np.median(im.reshape(-1, 3), axis=0)
            cast = float(med[0]) / max(float(med[2]), 1.0)
            say(f"  colour of {os.path.basename(latest)}: blue/red = {cast:.2f} (normal 0.95-1.10)")
            if cast > CAST_MAX:
                say("  WARN: blue colour cast (overcast light) -> leaf pixels drop out, GPR reads LOW")
                problems.append(f"{os.path.basename(latest)[:3]} blue colour cast")
        except Exception as e:  # noqa: BLE001
            say(f"  (colour check skipped: {e})")
    if aln:
        a = aln[-1]
        c = fnum(a.get("confidence"))
        say(f"  alignment D{a.get('day')}: shift ({a.get('dx_px')}, {a.get('dy_px')}) px, confidence {c}, applied {a.get('applied')}")
        if len(aln) >= 2:
            p = aln[-2]
            jump = ((fnum(a['dx_px']) - fnum(p['dx_px'])) ** 2 + (fnum(a['dy_px']) - fnum(p['dy_px'])) ** 2) ** 0.5
            if jump > 20:
                say(f"  WARN: camera moved {jump:.0f} px since the day before -> check the mount is tight")
                problems.append("camera moved")
        if c is not None and c < 0.25:
            say("  WARN: weak alignment match (< 0.25) -> look at the overlay before trusting the day")

    # ---------------------------------------------------------- GPR behaviour
    say("\n[3] Canopy (cell_gpr, % of pot area)")
    days = sorted(by_day)
    if len(days) >= 2:
        d1, d0 = days[-1], days[-2]
        cur = {r["pot_id"]: fnum(r.get("cell_gpr")) for r in by_day[d1]}
        prv = {r["pot_id"]: fnum(r.get("cell_gpr")) for r in by_day[d0]}
        fmt = lambda v: " -- " if v is None else f"{v:4.2f}"
        say("  pot    " + "  ".join(f"{p[-2:]:>4}" for p in POTS))
        say(f"  D{d0:<4} " + "  ".join(fmt(prv.get(p)) for p in POTS))
        say(f"  D{d1:<4} " + "  ".join(fmt(cur.get(p)) for p in POTS))
        drops = [p for p in POTS if prv.get(p) and cur.get(p) is not None and cur[p] < 0.7 * prv[p]]
        if len(drops) >= 7:
            say(f"  WARN: {len(drops)} of 9 pots fell >30% at once -> almost certainly light, not growth")
            problems.append(f"D{d1} GPR dropped in {len(drops)} pots")
        for p in POTS:
            last = [fnum(r.get("cell_gpr")) for d in days[-3:] for r in by_day[d] if r["pot_id"] == p]
            if len(last) >= 2 and all(v is not None and v <= 0.01 for v in last[-2:]):
                say(f"  CHECK {p}: GPR ~0 on the last 2 days -> is the seedling alive / visible?")
                problems.append(f"{p} GPR ~0")

    # ---------------------------------------------------------- soil moisture vs band
    say("\n[4] Soil moisture vs band (last 4 recorded days)")
    for p in POTS:
        lo, hi = BAND[GROUP[p]]
        vals = [(d, fnum(r.get("sm_pct"))) for d in days[-4:] if d >= BANDS_ON_DAY
                for r in by_day[d] if r["pot_id"] == p]
        vals = [(d, v) for d, v in vals if v is not None]
        if not vals:
            continue
        out = [v for _, v in vals if v < lo - 10 or v > hi + 10]
        line = " ".join(f"{v:.0f}" for _, v in vals)
        tag = ""
        if len(out) >= 3:
            tag = "   <-- far outside band 3+ days"
            problems.append(f"{p} outside band")
        say(f"  {p} {GROUP[p]:<6} band {lo}-{hi}: {line}{tag}")

    # ---------------------------------------------------------- logger alive
    say("\n[5] Logs")
    _, sm = read_csv(os.path.join(DATA, "sm_log.csv"))
    if sm:
        t = datetime.fromisoformat(sm[-1]["wall_time"])
        age = (now - t).total_seconds() / 3600
        say(f"  sm_log last row {t:%m-%d %H:%M} ({age:.1f} h ago)")
        if age > 1:
            say("  WARN: soil moisture log stopped -> pi-link not running? (sudo systemctl status pi-link)")
            problems.append("sm_log stale")
    else:
        say("  WARN: sm_log.csv missing")
    _, irr = read_csv(os.path.join(DATA, "irrigation_log.csv"))
    last_cnt, gaps = {}, []
    for r in irr:
        p, c = r.get("pot_id"), fnum(r.get("event_count"))
        if c is None:
            continue
        if p in last_cnt and c > last_cnt[p] + 1:
            gaps.append(f"{p}: count {int(last_cnt[p])} -> {int(c)} at {r['wall_time'][:16]}")
        last_cnt[p] = c
    say(f"  irrigation_log: {len(irr)} doses logged; doses per pot: "
        + ", ".join(f"{p[-2:]}={int(last_cnt[p])}" for p in sorted(last_cnt)))
    if gaps:
        say("  WARN: dose numbers skipped (doses not written to the log):")
        for g in gaps:
            say(f"      {g}")
    since = now - timedelta(hours=24)
    _, err = read_csv(os.path.join(DATA, "error_log.csv"))
    recent = collections.Counter()
    events, prev_key, prev_t = collections.Counter(), None, None
    for r in err:
        try:
            t = datetime.fromisoformat(r["wall_time"])
        except (KeyError, ValueError):
            continue
        key = (r.get("code"), (r.get("detail") or "").split(";")[0])
        # a repeat of the same code+pot within 20 min is the same event
        if key != prev_key or prev_t is None or (t - prev_t).total_seconds() > 1200:
            events[key[0]] += 1
        prev_key, prev_t = key, t
        if t >= since:
            recent[r.get("code")] += 1
    say(f"  error_log: {len(err)} lines = {sum(events.values())} separate events: "
        + ", ".join(f"{k} {v}" for k, v in events.most_common(6)))
    if recent:
        say("  last 24 h: " + ", ".join(f"{k} {v} lines" for k, v in recent.most_common()))
    _, pw = read_csv(os.path.join(DATA, "power_log.csv"))
    pr = [r for r in pw if r.get("logged_at", "") >= since.isoformat()[:19]]
    if pr:
        say(f"  power events in last 24 h: {len(pr)}  (" + "; ".join(
            (r.get('note') or r.get('event'))[:40] for r in pr[-3:]) + ")")

    # ---------------------------------------------------------- disk + backup
    say("\n[6] Storage")
    du = shutil.disk_usage(HOME)
    say(f"  free on SD card: {du.free / 1e9:.1f} GB")
    if du.free < 2e9:
        problems.append("disk below 2 GB")
    tars = sorted(glob.glob(os.path.join(BACKUPS, "data_*.tar.gz")))
    say(f"  latest backup: {os.path.basename(tars[-1]) if tars else 'NONE -> run ~/fixkit/backup.sh'}")
    usb = [m for m in glob.glob("/media/*/*") if os.path.ismount(m)]
    say(f"  USB drive: {usb[0] if usb else 'not plugged in'}")

    say("\n" + "=" * 72)
    say("SUMMARY: " + ("all OK" if not problems else "; ".join(problems)))

    if not args.no_save:
        os.makedirs(os.path.join(KIT, "reports"), exist_ok=True)
        path = os.path.join(KIT, "reports", f"check_{now:%Y-%m-%d_%H%M}.txt")
        with open(path, "w") as f:
            f.write("\n".join(out_lines) + "\n")
        print(f"(saved {path})")


if __name__ == "__main__":
    main()
