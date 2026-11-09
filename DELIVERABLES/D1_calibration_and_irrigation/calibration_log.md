# Two-point soil moisture calibration log (Deliverable 1)

AgriSentry, run 2 (sown 2026-10-29). Source of every number: `Dual_Archi/Dual_Archi_Firmware/src/main.cpp`.

## 1. Method (Section III.E.1)
| Point | How it was made | Reading taken as |
|---|---|---|
| Dry (0 %) | DA soil mix oven-dried at **150 °C for 6 h** (the oven's limit) | `dryADC` |
| Wet (100 %) | The same soil **fully saturated** with water | `wetADC` |

Calibration date: **2026-09-18**, using the same soil mixture as the pots
Done by: **Cedric Vince Tan**

Sensors: capacitive soil moisture sensor v1.2, one per pot, read by the ESP32-S3 through a multiplexer. Each reading is the median of 9 ADC samples.

## 2. Conversion used by the ESP32
```
moisture % = (dryADC - raw) / (dryADC - wetADC) x 100, limited to 0-100 %
```
**This is relative moisture between oven-dry and saturated soil, not true volumetric water content (VWC).** The treatment bands (30–40, 50–60, 70–80 %) are on this scale.

## 3. Calibration values per probe
| Pot | Group | dryADC (0 %) | wetADC (100 %) | Span | Offset |
|---|---|---|---|---|---|
| P-01 | Low | 2483 | 1120 | 1363 | none |
| P-02 | Low | 2483 | 1120 | 1363 | none |
| P-03 | Low | 2380 | 1017 | 1363 | −103 |
| P-04 | Optimal | 2483 | 1120 | 1363 | none |
| P-05 | Optimal | 2408 | 1045 | 1363 | −75 |
| P-06 | Optimal | 2483 | 1120 | 1363 | none |
| P-07 | High | 2483 | 1120 | 1363 | none |
| P-08 | High | 2483 | 1120 | 1363 | none |
| P-09 | High | 2483 | 1120 | 1363 | none |

## 4. Air check and offsets (2026-10-28)
All 9 probes were cleaned and held in air. Seven read 4.1–7.0 % (mean 5.9 %). **P-03 read 13.5 % and P-05 read 11.4 %**, so both their dry and wet points were shifted by the same count (P-03 −103, P-05 −75). After the shift they read like the others in air. The span (1363 counts) is unchanged, so the slope of the scale is the same for all 9 probes.

## 4b. Pot weighing (water held by the soil)
One filled pot weighed on a 5 kg / 1 g kitchen scale (photos from the team, sent 2026-11-09):

| State | Scale reading |
|---|---|
| Oven-dry soil (0 %) | **388 g** |
| Fully saturated (100 %) | **662 g** (pot sitting in a plastic bag) |
| Water held, dry → saturated | **274 g ≈ 274 mL** (minus the bag's few grams) |

So 1 % on this scale ≈ 2.7 mL of water. The firmware uses `ML_PER_PERCENT = 3.18` ("318 mL total field capacity", set 2026-09-15), so each dose is about 16 % larger than this weighing gives. The watering still stops at the band, because the probe is re-read every 15 min; the larger dose only makes a small overshoot more likely. Not changed mid-run.

## 4c. Conversion to true volumetric water content (VWC)
Soil in the pot (team measurement, 2026-11-09): bottom diameter 8.5 cm, top soil diameter 11 cm, soil depth 8 cm.
As a truncated cone: V = πh/3 × (R² + Rr + r²) = π·8/3 × (5.5² + 5.5·4.25 + 4.25²) ≈ **601 cm³ (601 mL)**.

Saturated soil holds 274 mL in 601 mL, so **100 % on our scale ≈ 45.6 % VWC**, a normal value for a potting mix.

```
true VWC (%) ≈ our % × 274 mL / 601 mL ≈ our % × 0.456
```

| Group | Band (relative %) | ≈ True VWC |
|---|---|---|
| Low (A) | 30–40 % | 13.7–18.2 % |
| Optimal (B) | 50–60 % | 22.8–27.4 % |
| High (C) | 70–80 % | 31.9–36.5 % |
| Saturated | 100 % | 45.6 % |
| Oven-dry | 0 % | 0 % |

Assumptions: the probe's reading is a straight line between the two calibration points (capacitive probes are close to linear but not exactly), the pot is evenly filled, and the 274 g includes the bag's few grams (≤ ~1 VWC point). With the firmware's 318 mL instead, saturation would be 52.9 % VWC. An optional harvest-day check (weighing known-volume cores before and after drying, at a few probe readings) would test the in-between values.

## 5. Fault limits
| Rule | Value |
|---|---|
| Valid raw ADC range | 150 to 4000. A reading outside it is logged as `SENSOR_RANGE` |
| Quarantine | 3 bad readings in a row: that pot's watering is suspended (`POD_QUARANTINE`) |
| Invalid calibration | dry = wet: logged as `CAL_INVALID`, no reading used |

## 6. Irrigation constants
| Constant | Value | Source |
|---|---|---|
| Flow per valve | **18 mL/s** | Measured 2026-10-12: 90 mL in 5 s, all 9 valves |
| Dose size | **3.18 mL per 1 % below target** | `ML_PER_PERCENT` |
| Maximum dose | 100 mL | `MAX_DOSE_ML` |
| Maximum valve pulse | 30 s (`PULSE_CLAMPED` if cut) | `MAX_PULSE_MS` |
| Wait after a dose | 2 h before the same pot can be dosed again | `STABILIZATION_MS` |
| Sampling | Every 15 min; logged every 30 min | `SAMPLE_INTERVAL_MS`, `SM_REPORT_INTERVAL_MS` |

Other hardware tests: relays and flow checked 2026-10-21; valve test 2026-10-29.

## 7. Treatment bands
| Group | Pots | Band | Active from |
|---|---|---|---|
| Germination (all pots) | P-01 to P-09 | 50–60 % | D1 (2026-10-29) to D8 11:44 |
| A Low | P-01, P-02, P-03 | 30–40 % | D8, 2026-11-05 11:44 (`bands-on`) |
| B Optimal | P-04, P-05, P-06 | 50–60 % | D8, 2026-11-05 11:44 |
| C High | P-07, P-08, P-09 | 70–80 % | D8, 2026-11-05 11:44 |

## 8. Limitations
- One shared two-point calibration for all probes, plus the two air-check offsets. No separate per-probe wet/dry calibration.
- Relative %, not VWC. Section 4c converts it (≈ × 0.456, from the pot weighing and soil volume), assuming a straight-line probe response.

Checked by: ______________  Date: ______________
