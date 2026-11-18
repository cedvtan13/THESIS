#!/usr/bin/env python3
"""remask_all.py -- Generate parallel clean-masked dataset and overlays from saved
Run 2 frames (D01, D04-D21) without touching the original baseline files.

Reads Dual_Archi/growth_dataset.csv (read-only) and writes:
  - Dual_Archi/growth_dataset_clean.csv
  - DATA/thesis_clean/growth_dataset.csv (+ sowing_date.txt, field_log.csv, glare_log.csv)
  - DATA/agrisentry_data/frames/overlay_clean/*.jpg

Uses PIL + numpy (no OpenCV dependency required).
Does NOT push to GitHub.
"""
import csv
import json
import os
import shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DUAL = os.path.join(REPO, "Dual_Archi")
THESIS_CLEAN = os.path.join(REPO, "DATA", "thesis_clean")
FRAME_DIR = os.path.join(REPO, "DATA", "agrisentry_data", "frames")
OVERLAY_CLEAN_DIR = os.path.join(FRAME_DIR, "overlay_clean")

CSV_PATH = os.path.join(DUAL, "growth_dataset.csv")
OUT_CLEAN_CSV = os.path.join(DUAL, "growth_dataset_clean.csv")
ALIGN_LOG = os.path.join(DUAL, "align_log.csv")

# Masking constants (aligned with updated Dual_Archi/capture_gpr.py)
HUE_LO, HUE_HI = 36, 85
SAT_MIN, VAL_MIN = 100, 55
WEAK_HUE_LO, WEAK_HUE_HI = 34, 88
WEAK_SAT_MIN, WEAK_VAL_MIN = 80, 48
MIN_BLOB_AREA = 12
POT_INNER_R_PX = 68.0
REF_R, REF_G, REF_B = 62.3, 72.3, 60.5

CELL_R_PX = 175.0
POT_PITCH_MM = 330.0        # same as capture_gpr.py (territory r = 221 px)
PX_PER_MM = 1.34
ANOMALY_DELTA_PER_DAY = 15.0

DAY_FRAMES = {
    1:  ("pot_rois_before_D6_recentre.json", (0.0, 0.0),   "D01_2026-10-29_1314.png"),
    4:  ("pot_rois_before_D6_recentre.json", (0.0, 0.0),   "D04_2026-11-01_1210.png"),
    5:  ("pot_rois_before_D6_recentre.json", (0.0, 0.0),   "D05_2026-11-02_1210.png"),
    6:  ("pot_rois_before_D6_recentre.json", (0.0, 0.0),   "D06_2026-11-03_1200.png"),
    7:  ("pot_rois_before_D10_align.json",   (0.0, 0.0),   "D07_2026-11-04_1200.png"),
    8:  ("pot_rois_before_D10_align.json",   (0.0, 0.0),   "D08_2026-11-05_1200.png"),
    9:  ("pot_rois_before_D10_align.json",   (0.0, 0.0),   "D09_2026-11-06_1200.png"),
    10: ("pot_rois_before_D11_rebase.json",  "2026-11-07 13:54", "D10_2026-11-07_1224.png"),
    11: ("pot_rois_before_D11_rebase.json",  "2026-11-08 12:52", "D11_2026-11-08_1252.png"),
    12: ("pot_rois.json",                    "2026-11-09 12:00", "replaced/D12_2026-11-09_1200.png"),
    13: ("pot_rois.json",                    "2026-11-10 12:00", "D13_2026-11-10_1200.png"),
    14: ("pot_rois.json",                    "2026-11-11 12:00", "D14_2026-11-11_1200.png"),
    15: ("pot_rois.json",                    "2026-11-12 12:10", "D15_2026-11-12_1210.png"),
    16: ("pot_rois.json",                    "2026-11-13 12:00", "D16_2026-11-13_1200.png"),
    17: ("pot_rois.json",                    "2026-11-14 12:00", "D17_2026-11-14_1200.png"),
    18: ("pot_rois.json",                    "2026-11-15 12:00", "D18_2026-11-15_1200.png"),
    19: ("pot_rois.json",                    "2026-11-16 12:47", "D19_2026-11-16_1247.png"),
    20: ("pot_rois.json",                    "2026-11-17 12:41", "D20_2026-11-17_1242.png"),
    21: ("pot_rois.json",                    "2026-11-18 12:54", "D21_2026-11-18_1254.png"),
}


def sunny_wb_rgb(rgb):
    """Normalize RGB frame to sunny-day neutral reference on mid-tone pixels."""
    f = rgb.astype(np.float32)
    lum = f.mean(axis=2)
    valid = (lum > 15) & (lum < 235)
    if np.count_nonzero(valid) < 1000:
        valid = np.ones(rgb.shape[:2], dtype=bool)
    rm = float(f[..., 0][valid].mean())
    gm = float(f[..., 1][valid].mean())
    bm = float(f[..., 2][valid].mean())
    out = np.empty_like(f)
    out[..., 0] = f[..., 0] * (REF_R / max(rm, 1.0))
    out[..., 1] = f[..., 1] * (REF_G / max(gm, 1.0))
    out[..., 2] = f[..., 2] * (REF_B / max(bm, 1.0))
    return np.clip(out, 0, 255).astype(np.uint8)


def rgb_to_cv_hsv(rgb):
    """OpenCV-compatible uint8 HSV (H: 0..179, S: 0..255, V: 0..255)."""
    arr = rgb.astype(np.float32) / 255.0
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    df = mx - mn

    h = np.zeros_like(mx)
    nz = df > 1e-6
    mr = nz & (mx == r)
    mg = nz & (mx == g) & ~mr
    mb = nz & (mx == b) & ~mr & ~mg

    h[mr] = (60.0 * ((g[mr] - b[mr]) / df[mr])) % 360.0
    h[mg] = 60.0 * ((b[mg] - r[mg]) / df[mg]) + 120.0
    h[mb] = 60.0 * ((r[mb] - g[mb]) / df[mb]) + 240.0

    s = np.zeros_like(mx)
    s[mx > 1e-6] = (df[mx > 1e-6] / mx[mx > 1e-6]) * 255.0
    v = mx * 255.0

    out = np.empty(rgb.shape, dtype=np.uint8)
    out[..., 0] = np.clip(np.round(h / 2.0), 0, 179).astype(np.uint8)
    out[..., 1] = np.clip(np.round(s), 0, 255).astype(np.uint8)
    out[..., 2] = np.clip(np.round(v), 0, 255).astype(np.uint8)
    return out


def morph_open_3x3(mask):
    """Exact 3x3 morphological opening (erode then dilate)."""
    m = mask > 0
    p = np.pad(m, 1, mode="edge")
    er = (
        p[:-2, :-2] & p[:-2, 1:-1] & p[:-2, 2:] &
        p[1:-1, :-2] & p[1:-1, 1:-1] & p[1:-1, 2:] &
        p[2:, :-2] & p[2:, 1:-1] & p[2:, 2:]
    )
    p2 = np.pad(er, 1, mode="constant", constant_values=False)
    di = (
        p2[:-2, :-2] | p2[:-2, 1:-1] | p2[:-2, 2:] |
        p2[1:-1, :-2] | p2[1:-1, 1:-1] | p2[1:-1, 2:] |
        p2[2:, :-2] | p2[2:, 1:-1] | p2[2:, 2:]
    )
    return di


def shift_rois(rois, dx, dy):
    out = {}
    for pid, r in rois.items():
        r2 = dict(r)
        r2["x"] = int(round(r["x"] + dx))
        r2["y"] = int(round(r["y"] + dy))
        out[pid] = r2
    return out


def roi_geometry(roi):
    return (roi["x"] + roi["w"] / 2.0,
            roi["y"] + roi["h"] / 2.0,
            min(roi["w"], roi["h"]) / 2.0)


def circle_mask(shape_hw, cx, cy, r):
    h, w = shape_hw
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return ((xx - int(cx)) ** 2 + (yy - int(cy)) ** 2) <= (int(r) * int(r))


def cell_masks(shape_hw, rois, r_px=CELL_R_PX):
    h, w = shape_hw
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    best = np.full((h, w), np.inf, np.float32)
    owner = np.full((h, w), -1, np.int8)
    ids = sorted(rois)
    for i, pid in enumerate(ids):
        cx, cy, _ = roi_geometry(rois[pid])
        d2 = (xx - cx) ** 2 + (yy - cy) ** 2
        closer = d2 < best
        best[closer] = d2[closer]
        owner[closer] = i
    owner[best > r_px * r_px] = -1
    return {pid: (owner == i) for i, pid in enumerate(ids)}


def clean_green_and_raw(hsv, rois):
    """Return (final_mask, raw_inner_hsv_mask)."""
    raw_hsv = (
        (hsv[..., 0] >= HUE_LO) & (hsv[..., 0] <= HUE_HI) &
        (hsv[..., 1] >= SAT_MIN) & (hsv[..., 2] >= VAL_MIN)
    )
    core = morph_open_3x3(raw_hsv)
    h, w = hsv.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    inner = np.zeros((h, w), dtype=bool)
    for r in rois.values():
        cx, cy, _ = roi_geometry(r)
        inner |= ((xx - cx) ** 2 + (yy - cy) ** 2) <= (POT_INNER_R_PX ** 2)

    visited = np.zeros((h, w), dtype=bool)
    clean_core = np.zeros((h, w), dtype=bool)
    ys, xs = np.nonzero(core & inner)
    for y0, x0 in zip(ys, xs):
        if visited[y0, x0]:
            continue
        stack = [(y0, x0)]
        visited[y0, x0] = True
        comp = []
        while stack:
            y, x = stack.pop()
            comp.append((y, x))
            for dy in (-1, 0, 1):
                ny = y + dy
                if 0 <= ny < h:
                    for dx in (-1, 0, 1):
                        nx = x + dx
                        if 0 <= nx < w and core[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            stack.append((ny, nx))
        if len(comp) >= MIN_BLOB_AREA:
            for y, x in comp:
                clean_core[y, x] = True

    weak = (
        (hsv[..., 0] >= WEAK_HUE_LO) & (hsv[..., 0] <= WEAK_HUE_HI) &
        (hsv[..., 1] >= WEAK_SAT_MIN) & (hsv[..., 2] >= WEAK_VAL_MIN)
    )
    p2 = np.pad(clean_core, 1, mode="constant", constant_values=False)
    dil = (
        p2[:-2, :-2] | p2[:-2, 1:-1] | p2[:-2, 2:] |
        p2[1:-1, :-2] | p2[1:-1, 1:-1] | p2[1:-1, 2:] |
        p2[2:, :-2] | p2[2:, 1:-1] | p2[2:, 2:]
    )
    final = (clean_core | (dil & weak)) & inner
    return final, (raw_hsv & inner)


def canopy_bbox(mask, area):
    """Bounding box (w, h) of largest 8-connected component of mask & area."""
    sub = mask & area
    if not np.any(sub):
        return 0, 0
    h, w = sub.shape
    visited = np.zeros((h, w), dtype=bool)
    best_area = 0
    best_wh = (0, 0)
    ys, xs = np.nonzero(sub)
    for y0, x0 in zip(ys, xs):
        if visited[y0, x0]:
            continue
        stack = [(y0, x0)]
        visited[y0, x0] = True
        min_x = max_x = x0
        min_y = max_y = y0
        cnt = 0
        while stack:
            y, x = stack.pop()
            cnt += 1
            if x < min_x: min_x = x
            if x > max_x: max_x = x
            if y < min_y: min_y = y
            if y > max_y: max_y = y
            for dy in (-1, 0, 1):
                ny = y + dy
                if 0 <= ny < h:
                    for dx in (-1, 0, 1):
                        nx = x + dx
                        if 0 <= nx < w and sub[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            stack.append((ny, nx))
        if cnt > best_area:
            best_area = cnt
            best_wh = (max_x - min_x + 1, max_y - min_y + 1)
    return best_wh


def draw_overlay(rgb, green_mask, cells, rois, out_path):
    """Save magenta-mask + yellow cell-boundary overlay JPEG."""
    ov = rgb.copy()
    ov[green_mask] = [255, 0, 255]
    # Draw cell boundaries (1-2 px border where neighbor differs)
    boundary = np.zeros(rgb.shape[:2], dtype=bool)
    for m in cells.values():
        p = np.pad(m, 1, mode="constant", constant_values=False)
        er = p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
        edge = m & ~er
        boundary |= edge
    # Thicken slightly to 2 px
    p = np.pad(boundary, 1, mode="constant", constant_values=False)
    thick = boundary | p[:-2, 1:-1] | p[1:-1, :-2]
    ov[thick] = [255, 255, 0]

    im = Image.fromarray(ov)
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
    except Exception:
        font = ImageFont.load_default()
    for pid, r in sorted(rois.items()):
        cx, cy, _ = roi_geometry(r)
        draw.text((int(cx) - 30, int(cy) - 72), pid, fill=(255, 255, 0), font=font)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    im.save(out_path, quality=88)


def load_shifts():
    shifts = {}
    with open(ALIGN_LOG, newline="") as f:
        for r in csv.DictReader(f):
            if r["applied"] == "1":
                shifts[(int(r["day"]), r["timestamp"])] = (float(r["dx_px"]), float(r["dy_px"]))
    return shifts


def main():
    shifts = load_shifts()
    with open(CSV_PATH, newline="") as f:
        rd = csv.reader(f)
        header = next(rd)
        rows = list(rd)
    col = {h: i for i, h in enumerate(header)}

    os.makedirs(OVERLAY_CLEAN_DIR, exist_ok=True)
    os.makedirs(THESIS_CLEAN, exist_ok=True)

    # Group rows by day
    days_present = sorted({int(r[col["day"]]) for r in rows})
    terr_r_px = (POT_PITCH_MM * PX_PER_MM) / 2.0

    roi_cache = {}
    prev_gpr = {}

    for day in days_present:
        if day not in DAY_FRAMES:
            raise SystemExit(f"ERROR: No frame mapping configured for D{day}")
        roi_file, shift_spec, rel_frame = DAY_FRAMES[day]
        frame_path = os.path.join(FRAME_DIR, rel_frame)
        if not os.path.exists(frame_path):
            raise SystemExit(f"ERROR: Missing frame {frame_path}")

        if roi_file not in roi_cache:
            with open(os.path.join(DUAL, roi_file)) as f:
                roi_cache[roi_file] = json.load(f)["rois"]
        base_rois = roi_cache[roi_file]
        if isinstance(shift_spec, tuple):
            dx, dy = shift_spec
        else:
            dx, dy = shifts[(day, shift_spec)]
        rois = shift_rois(base_rois, dx, dy)

        rgb = np.array(Image.open(frame_path).convert("RGB"))
        wb = sunny_wb_rgb(rgb)
        hsv = rgb_to_cv_hsv(wb)
        green_all, green_raw = clean_green_and_raw(hsv, rois)
        cells = cell_masks(rgb.shape[:2], rois)

        day_rows = [r for r in rows if int(r[col["day"]]) == day]
        if len(day_rows) != 9:
            raise SystemExit(f"ERROR: Expected 9 rows for D{day}, found {len(day_rows)}")

        for r in day_rows:
            pid = r[col["pot_id"]]
            roi = rois[pid]
            cx, cy, rad = roi_geometry(roi)
            area = circle_mask(rgb.shape[:2], cx, cy, rad)
            tot = int(np.count_nonzero(area))
            g = int(np.count_nonzero(green_all & area))
            gr = int(np.count_nonzero(green_raw & area))
            cw, ch = canopy_bbox(green_all, area)

            t_area = circle_mask(rgb.shape[:2], cx, cy, terr_r_px)
            tt = int(np.count_nonzero(t_area))
            tg = int(np.count_nonzero(green_all & t_area))

            ct = int(np.count_nonzero(cells[pid]))
            cg = int(np.count_nonzero(green_all & cells[pid]))

            gpr = g / tot * 100.0 if tot else 0.0
            gpr_raw = gr / tot * 100.0 if tot else 0.0
            tgpr = tg / tt * 100.0 if tt else 0.0
            cgpr = cg / ct * 100.0 if ct else 0.0

            flag = 0
            if pid in prev_gpr:
                pday, pg = prev_gpr[pid]
                if abs(gpr - pg) > ANOMALY_DELTA_PER_DAY * max(1, day - pday):
                    flag = 1
            prev_gpr[pid] = (day, gpr)

            r[col["raw_gpr"]] = f"{gpr:.2f}"
            r[col["green_px"]] = str(g)
            r[col["total_px"]] = str(tot)
            r[col["flag"]] = str(flag)
            r[col["raw_gpr_noopen"]] = f"{gpr_raw:.2f}"
            r[col["terr_gpr"]] = f"{tgpr:.2f}"
            r[col["terr_green_px"]] = str(tg)
            r[col["terr_total_px"]] = str(tt)
            r[col["canopy_w_px"]] = str(cw)
            r[col["canopy_h_px"]] = str(ch)
            r[col["cell_gpr"]] = f"{cgpr:.2f}"
            r[col["cell_green_px"]] = str(cg)
            r[col["cell_total_px"]] = str(ct)

        # Write clean overlays to overlay_clean/ only (never touch original overlay/)
        ov_path = os.path.join(OVERLAY_CLEAN_DIR, f"D{day:02d}_overlay.jpg")
        if day == 12:
            ov_1200 = os.path.join(OVERLAY_CLEAN_DIR, "D12_overlay_1200.jpg")
            draw_overlay(rgb, green_all, cells, rois, ov_1200)
            shutil.copy2(ov_1200, ov_path)
        else:
            draw_overlay(rgb, green_all, cells, rois, ov_path)

        mean_cell = np.mean([float(r[col["cell_gpr"]]) for r in day_rows])
        mean_raw = np.mean([float(r[col["raw_gpr"]]) for r in day_rows])
        p3_px = [r[col["green_px"]] for r in day_rows if r[col["pot_id"]] == "P-03"][0]
        print(f"D{day:02d}: raw_gpr mean={mean_raw:.2f}%, cell_gpr mean={mean_cell:.2f}% (P-03={p3_px} px)")

    # Write clean CSV & supporting metadata to parallel clean paths
    with open(OUT_CLEAN_CSV, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    shutil.copy2(OUT_CLEAN_CSV, os.path.join(THESIS_CLEAN, "growth_dataset.csv"))
    for fname in ("sowing_date.txt", "field_log.csv", "glare_log.csv"):
        src = os.path.join(DUAL, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(THESIS_CLEAN, fname))
    print(f"\nWrote {os.path.relpath(OUT_CLEAN_CSV, REPO)} ({len(rows)} rows) and DATA/thesis_clean/")
    print(f"Wrote clean overlays to {os.path.relpath(OVERLAY_CLEAN_DIR, REPO)}/")


if __name__ == "__main__":
    main()
