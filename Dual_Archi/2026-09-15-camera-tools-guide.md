# Camera Tools — Paths, `cam_check.py`, and `stream_preview.py`

Group B thesis rig · 15 September 2026

Three parts: how Linux paths work, then each tool.

---

# PART 1 — Paths on the Pi

Everything about "where do the images go" comes down to one distinction.

## Absolute vs relative

An **absolute path** starts with `/`. It means the same thing no matter where you are standing:

```
/home/ced/thesis/camcheck/capture.jpg
```

A **relative path** does not start with `/`. It is interpreted from your *current directory*:

```
camcheck/capture.jpg        -> <wherever you are>/camcheck/capture.jpg
```

`pwd` tells you where you are standing. `cd` moves you.

```bash
pwd                 # /home/ced
cd ~/thesis
pwd                 # /home/ced/thesis
```

**This is the single most common source of "where did my file go?"** If you run a script from a different directory than usual and it saved to a relative path, the output moved with you.

## The four shorthands

| Symbol | Means | Example |
|---|---|---|
| `~` | your home directory | `~/thesis` → `/home/ced/thesis` |
| `.` | the current directory | `./capture.jpg` |
| `..` | one directory up | `../pot_rois.json` |
| `/` | the root of the filesystem | `/media/usb` |

`~` is expanded by the **shell**, not by Python. That matters:

```bash
python3 cam_check.py --out-dir ~/Pictures     # shell expands ~ -> /home/ced/Pictures  ✓
python3 cam_check.py --out-dir '~/Pictures'   # quoted: shell does NOT expand it
```

The quoted version would normally create a literal folder named `~`. `cam_check.py` calls
`os.path.expanduser()` on whatever it receives, so it survives that mistake — but do not
rely on every program being that forgiving.

## Spaces in paths

A space separates arguments. A path with a space in it must be quoted:

```bash
python3 cam_check.py --out-dir "~/My Photos/day 0"     # ✓
python3 cam_check.py --out-dir ~/My Photos/day 0       # ✗ three arguments
```

This is why Linux people use `day0` and `day_0` instead of `day 0`.

## Where things actually live on your Pi

```
/home/ced/                      your home. "~" is this.
└── thesis/                     THESIS_BASE
    ├── capture_gpr.py
    ├── pi_bench.py
    ├── cam_check.py
    ├── pot_rois.json           the nine ROI circles
    ├── growth_dataset.csv      the 315 rows you are building
    └── camcheck/               images from cam_check.py   <- OUT_DIR
        ├── capture.jpg
        ├── capture_mask.png
        ├── rois.jpg
        └── focus_0.82.jpg
```

## Checking and moving files

```bash
ls ~/thesis/camcheck/                 # what is in there
ls -lh ~/thesis/camcheck/             # with sizes and dates
du -sh ~/thesis/camcheck/             # how big is the folder
realpath ~/thesis/camcheck            # resolve to an absolute path
df -h /                               # free space on the SD card
```

## Getting images onto your laptop

You cannot view a JPEG over plain SSH. Three ways:

**1. `scp`** — from your *laptop's* PowerShell, not from inside SSH:

```powershell
scp ced@groupb.local:~/thesis/camcheck/*.jpg .
scp -r ced@groupb.local:~/thesis/camcheck "C:\Users\ACER\ThesisCoWork\camcheck"
```

The `.` at the end means "into my current folder". `-r` means recursive, for a whole directory.

**2. A one-off web server** — quickest for a quick look:

```bash
cd ~/thesis/camcheck
python3 -m http.server 8080
```

Then open `http://groupb.local:8080/` in your browser. Ctrl-C to stop. Anyone on your
network can read that folder while it runs, so stop it when you are done.

**3. VS Code Remote-SSH** — connect to the Pi and images open in the editor. Most
comfortable if you are already living in VS Code.

---

# PART 2 — `cam_check.py`

Not a live view. It asks: **is the image good enough to measure from?**

## How it decides where to save

Three levels, each overriding the one above:

```
1. built-in default     ~/thesis/camcheck
2. environment variable CAMCHECK_OUT, or THESIS_BASE
3. command-line flag    --out-dir          <- wins
```

```bash
# 1. default
python3 cam_check.py --check
#    [cam_check] images -> /home/ced/thesis/camcheck

# 2. for this shell session only
export CAMCHECK_OUT=~/Pictures/camcheck
python3 cam_check.py --check
#    [cam_check] images -> /home/ced/Pictures/camcheck

# 3. just this one run
python3 cam_check.py --check --out-dir /media/usb/day0
#    [cam_check] images -> /media/usb/day0
```

`export` lasts until you close the SSH session. To make it permanent, add the line to
`~/.bashrc`. `unset CAMCHECK_OUT` cancels it.

`THESIS_BASE` moves the images **and** `pot_rois.json` together:

```bash
export THESIS_BASE=/mnt/ssd/thesis
# -> images  /mnt/ssd/thesis/camcheck
# -> rois    /mnt/ssd/thesis/pot_rois.json
```

The first line of every run prints where it is writing. **Read that line.** It is there
so you never have to guess.

## Filenames are fixed — this matters

Each run writes the same names and overwrites the last:

`capture.jpg` · `capture_mask.png` · `check_1.jpg` · `check_2.jpg` · `rois.jpg` · `focus_<lp>.jpg`

So to compare two setups, give each its own folder:

```bash
python3 cam_check.py --check --out-dir ~/camcheck/h1650
# raise the camera
python3 cam_check.py --check --out-dir ~/camcheck/h1350
```

Now `~/camcheck/h1650/rois.jpg` and `~/camcheck/h1350/rois.jpg` sit side by side and you
can actually see which height keeps all nine pots in frame.

Dated folders work well for daily checks:

```bash
python3 cam_check.py --check --out-dir ~/camcheck/$(date +%F)
# $(date +%F) expands to 2026-09-15
```

## The five modes

### `--info` — start here

```bash
python3 cam_check.py --info
```

Lists cameras and sensor modes. No image is captured, nothing is saved.

Look for **`imx708`** (Camera Module 3, VFOV 41°) or **`imx219`** (Module V2, VFOV 48.8°).
Your manuscript Section III.B still names the V2 — different geometry, different mounting
height. This tells you which one is really on the rig.

Also check that a sensor mode matches **2304×1296**. If none does, libcamera crops or
scales, and a crop means a narrower field of view than your height calculation assumed.

### `--capture` — one still, with numbers

```bash
python3 cam_check.py --capture
python3 cam_check.py --capture --auto     # same shot with AE/AF left on
```

Saves `capture.jpg` and `capture_mask.png`, and prints:

| Reading | Want | If it is wrong |
|---|---|---|
| mean brightness | 80–180 | under 60, `V>40` rejects shadowed leaf, GPR reads low |
| blown-out % | < 1 % | clipped leaves lose saturation, drop out of the band, GPR reads **low** |
| crushed black % | < 1 % | shadow detail gone |
| sharpness | compare only | meaningless as an absolute number |
| green pixels % | — | your actual measurement |

Running it twice — once normally, once with `--auto` — shows you what locking the camera
is actually doing.

**Open `capture_mask.png`.** Leaves white, everything else black. That one image tells you
whether the HSV band is selecting your Pechay, and it is the fastest check in the whole
toolkit.

### `--focus-sweep` — the one with 35-day consequences

```bash
python3 cam_check.py --focus-sweep --distance 1.22
```

`LensPosition` is measured in **dioptres = 1 ÷ distance in metres.**

| Distance to subject | LensPosition |
|---|---|
| infinity | 0.0 |
| 2.0 m | 0.50 |
| 1.22 m | 0.82 |
| 1.0 m | 1.00 |
| 0.40 m | 2.50 |

`--distance` is lens to **canopy**, not lens to floor. At 1650 mm camera height with
~430 mm of pot-plus-plant, that is 1.22 m.

The sweep steps through nine positions around your estimate, scores each by Laplacian
variance, saves every frame, and recommends one. Put a printed page of text at the canopy
plane before running it — focusing on bare soil gives the algorithm nothing to grip.

Then hardcode the winner in `capture_gpr.py`:

```python
"LensPosition": 0.82,
```

**Why this matters more than it looks.** If autofocus hunts between days, edge sharpness
changes and the green pixel count drifts with no change in the plant. Your model would be
fitting lens behaviour, not growth.

Two cautions the script prints for you: if the best value lands at the *edge* of the
sweep, the true optimum is outside it — re-run with a better `--distance`. And Laplacian
variance also rewards noise and moving leaves, so confirm by eye in `focus_*.jpg`.

### `--rois` — the silent-failure check

```bash
python3 cam_check.py --rois
```

Captures one frame, overlays the circles from `pot_rois.json`, prints a table, saves
`rois.jpg`. Green circle = inside the frame. **Red = clipped.**

A clipped ROI does not raise an error. It measures a smaller area, and that pot's GPR is
wrong for all 35 days while looking perfectly plausible in the CSV. This is the check that
catches it before the data exists.

Point it at a different ROI file with `--roi-file`:

```bash
python3 cam_check.py --rois --roi-file ~/thesis/rois_v2.json
```

### `--check` — everything

```bash
python3 cam_check.py --check
```

Runs `--info`, a locked capture, **a repeatability test**, then `--rois`.

The repeatability test is the part you cannot get anywhere else: two frames five seconds
apart with nothing moving. With controls locked they should be near-identical.

| Reading | Want |
|---|---|
| green delta | < 0.10 pp |
| brightness delta | < 2.0 |

Fail either and something is still auto-adjusting. **An unstable camera makes GPR
unusable** — you would be measuring the camera, not the plant.

Run this before D=1. Then open every file it wrote.

---

# PART 3 — `stream_preview.py`

Different job. `cam_check.py` signs off on a camera that is already pointed correctly.
`stream_preview.py` is how you point it — a live browser view while your hands are on the
mount.

## Start it

```bash
cd ~/thesis
python3 stream_preview.py
```

It prints its own URL:

```
[preview] 1024x576  ->  http://192.168.1.3:8000/
[preview] Ctrl-C to stop
```

Open that on your laptop. Ctrl-C on the Pi to stop.

## Its flags

```bash
python3 stream_preview.py --port 8080
python3 stream_preview.py --width 1280
python3 stream_preview.py --roi-file ~/thesis/rois_v2.json
python3 stream_preview.py --lock-exposure
```

**It saves nothing** — that is why it has no `--out-dir`. It is a live stream only. To
keep a frame, use `cam_check.py --capture`.

Keep `--width` at a **16:9** value (1024, 1280, 1600). The still capture is 2304×1296,
which is 16:9, and the ROI overlay scales by that assumption. A 4:3 width misaligns every
circle.

## The four modes

Buttons on the page, or `?mode=` in the URL.

| Mode | Shows | Use it to |
|---|---|---|
| `normal` | thirds grid + centre crosshair | level the frame, centre the array |
| `roi` | the nine circles from `pot_rois.json` | confirm every pot is inside — red = falling off |
| `mask` | only what the HSV band selects | point at real leaves; they must light up |
| `gpr` | circles + live per-pot % | watch the number move as you adjust |

## The order to use them in

1. **`normal`** — get the array square in the frame using the grid.
2. **`roi`** — every circle green. One red circle means raise the camera or re-run `make_rois.py`.
3. **`mask`** — hold a real Pechay leaf in view. It must turn white. If leaves stay black, your HSV band is wrong.
4. **`gpr`** — final sanity check that the numbers are plausible before you walk away.

## On `mask` mode

This is the HSV calibration task. The band is `H 35–85` in **OpenCV hue units (0–179)**,
not degrees.

Do **not** "convert" 35–85 to 17–42 by halving. That was tested and returns 0.00 % GPR on a
healthy green canopy, because it selects orange-yellow instead of green. Keep the code as
it is and fix the manuscript text, not the other way round.

## On `--lock-exposure`

Without it the preview auto-exposes and looks nicer. With it, you see what
`capture_gpr.py` will actually see.

**Aim with `--lock-exposure` on.** A preview that has quietly brightened the scene is not
telling you the truth about your measurement.

Note the flag currently applies `LensPosition: 2.5`, which is 40 cm — wrong for this rig.
Once `--focus-sweep` gives you the real value, change it in `stream_preview.py` too so both
tools agree.

## Startup line worth reading

```
[preview] sensor output: (2304, 1296)  (want 2304x1296)
```

If those disagree, the preview's field of view is not the same as the still capture, and
aiming with it is not valid. Tell me if that happens.

---

# Which tool, when

| Situation | Tool |
|---|---|
| mounting or moving the camera | `stream_preview.py`, mode `roi` |
| checking the HSV band on real leaves | `stream_preview.py`, mode `mask` |
| choosing a mounting height | `cam_check.py --rois --out-dir` per height |
| locking focus | `cam_check.py --focus-sweep` |
| signing off before D=1 | `cam_check.py --check` |
| daily spot-check during the run | `cam_check.py --capture --out-dir ~/camcheck/$(date +%F)` |

**Never run both at once.** The camera is a single-access device — the second one to start
will fail with a "device busy" error.

---

# Cheat sheet

```bash
# where am I, what is here
pwd ; ls -lh ~/thesis/camcheck/

# change output for one run
python3 cam_check.py --check --out-dir ~/camcheck/test1

# change it for the session
export CAMCHECK_OUT=~/Pictures/camcheck

# move rois AND images together
export THESIS_BASE=/mnt/ssd/thesis

# dated folder
python3 cam_check.py --check --out-dir ~/camcheck/$(date +%F)

# pull to laptop (run in PowerShell, not in SSH)
scp -r ced@groupb.local:~/thesis/camcheck "C:\Users\ACER\ThesisCoWork\camcheck"

# quick browser look instead
cd ~/thesis/camcheck && python3 -m http.server 8080

# aim the rig
python3 stream_preview.py --lock-exposure
```
