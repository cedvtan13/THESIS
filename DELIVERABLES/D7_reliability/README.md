# Reliability evidence so far (Deliverable 7), D1–D8

Snapshot taken 2026-11-05 (D8). The full summary is produced again at D30 with `python3 Dual_Archi/reliability_report.py --days 30`.

## Files
| File | What it is |
|---|---|
| `reliability_summary_D08.txt` | Output of `reliability_report.py`: captures, irrigation, band adherence, faults |
| `error_log.csv` | Faults the ESP32 reported (sensor range, quarantine, pulse limits) |
| `power_log.csv` | Every Pi restart, detected on the next boot |
| `throttle_log.csv` | The Pi's under-voltage flag, temperature and Wi-Fi state, every 5 min (from 2026-11-04 21:56) |
| `vision/` | **Vision reliability:** ROI drift checks, GPR accuracy against hand labels, empty-pot false positives, exposure and glare checks. Start with `vision/README.md` |

## Main findings so far
- **Noon captures: 6 of 8 due (75 %).** D2 and D3 missed because the Pi had no power at noon. Not back-filled.
- **Fault log: 0 sensor or valve faults.**
- **Power events: 49 since sowing** (38 Pi only, 11 Pi and ESP32 together), worst on Nov 3 (22).
  - The Pi's under-voltage flag stayed at 0 throughout `throttle_log.csv`.
  - 2026-11-05: the 12 V supply was upgraded from 1 A to 2.5 A.
- **Irrigation: 1 automatic dose** so far (P-02, 2026-11-05 11:25, 16.2 mL, during germination mode).
- **Band adherence in germination (D1–D8) was low:** most pots stayed above 60 % because of hand watering after sowing (logged deviations) and wet soil. The system correctly did not water pots that were above band.

- **Vision:** GPR vs hand labels IoU 0.64 (people 0.79), error 0.28 pp, bias +0.04 pp. Empty pots read 0.00 in 23 of 24 photos. 10 of 54 pot photos flagged for light, fixed with cloths on D8. Details in `vision/README.md`.

## Note on the summary
`reliability_summary_D08.txt` counts the whole of 2026-11-05 as treatment phase. The bands were actually switched on at 11:44 that day.
