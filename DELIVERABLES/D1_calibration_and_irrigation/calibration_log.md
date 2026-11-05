# Two-point soil moisture calibration log (Deliverable 1)

AgriSentry, run 2 (sown 2026-10-29). Source of every number: `Dual_Archi/Dual_Archi_Firmware/src/main.cpp`.

## 1. Method (Section III.E.1)
| Point | How it was made | Reading taken as |
|---|---|---|
| Dry (0 %) | DA soil mix oven-dried at **150 °C for 6 h** (the oven's limit) | `dryADC` |
| Wet (100 %) | The same soil **fully saturated** with water | `wetADC` |

Calibration date: ______________ (before run 1; team to fill in)
Done by: ______________

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
- Relative %, not VWC. An optional harvest-day check (weighing known-volume soil cores before and after drying) can convert the bands to true VWC.

Checked by: ______________  Date: ______________
