# Question-and-answer prep for the Nov 21 project checking

**Started:** Nov 18, 2026 (D21). **Data used:** repo state after the Nov 17 16:06 pull (`pi_pulls/2026-11-17_1606`), D1 to D20. Update the numbers after the D21 to D23 pulls.

**How to answer every question:** three parts, short.
1. **The honest fact**, with a number.
2. **Why**, with our evidence or a source.
3. **What we learned or changed.**

Don't argue, don't over-explain. If you don't know, say "we'll check and include it in the revision".

**Rule for every answer:** numbers come from the files listed, as measured. Nothing estimated is presented as measured.

**Status of sources:**
- **Verified** = the paper was read for this document.
- **In our references** = cited in the manuscript (v8).
- **To verify** = check the paper before citing it on a slide.

| Source | Used for | Status |
|---|---|---|
| Zamora, Ogue and Manila (2025), USC B.S. thesis | 1:1 valve-per-pot design | In our references |
| Poorter et al. (2012), *Functional Plant Biology* 39, 839–850, doi:10.1071/FP12049 | pot size limits growth | **Verified** (Nov 18) |
| Blom and Piott (1992), *J. Amer. Soc. Hort. Sci.* 117(2), 220–223 | top vs bottom watering | **Verified** (Nov 18) |
| Fadilah, Lakitan and Marlina (2022), *Agronomy Research* 20(S1), 938–950, doi:10.15159/ar.22.057 | pak choi prefers full sun | **Verified**, abstract only (Nov 18) |
| Harrell (2015), *Regression Modeling Strategies*, 2nd ed., Springer | observations per predictor | In our references; **to verify** the exact page and ratio |
| Standard method for soil pH in a soil-water mix (e.g. ISO 10390) | pH method | **To verify** before Thursday |

---

## Q1. Why pots, not plots?

**Fact:**
- Each plant is in its own pot with its own probe and its own valve: 9 pots, 9 probes, 9 valves.
- The pots are 0.60 L truncated cones (110 mm top, 85 mm base, 80 mm deep), not the 200 mm pots in the proposal. We changed to a standard pot that was available locally (Chapter 3).

**Why:**
- One probe and one valve per plant means each plant's water is measured and controlled on its own. This is the 1:1 design we adapted from Zamora et al. (2025).
- The model predicts each plant's weight from that plant's canopy and moisture. That needs one moisture record per plant; a plot would mix several plants under one probe.

**The honest trade-off:**
- Pot size limits growth. Poorter et al. (2012), a meta-analysis of 65 studies: on average, doubling the pot size increased biomass by 43%. Smaller pots reduce growth mainly by lowering photosynthesis per leaf area.
- Their guideline: plant biomass should not exceed about 1 g per litre of pot. For our 0.60 L pots, that is about 0.6 g.
- All 9 pots are identical, so the comparison between treatments stays fair, but absolute growth is limited.

**What we learned / would change:** use at least the proposal's 200 mm pots, sized to the expected harvest weight with Poorter's guideline.

**Evidence:** manuscript Chapter 3 (pot dimensions); `Dual_Archi_Firmware/src/main.cpp` lines 76–86 (one band per pot).

## Q2. Why water from the top, not the bottom?

**Fact:**
- Each pot gets water through its own drip tube onto the soil surface, from a solenoid valve.
- The emitter position relative to the probe is not the same in every pot. P-06's outlet is at the pot edge, a few cm from its probe (photos Nov 17), and P-06 jumps 25 to 35 points after each dose of about 17 mL.

**Why:**
- A per-pot valve with a drip outlet is how the 1:1 system delivers a measured volume to one pot only (Zamora et al., 2025).
- The probe reads the upper root zone, where top water arrives.
- Top watering is not worse for growth by itself. Blom and Piott (1992), potted chrysanthemum: top (Chapin) irrigation gave 24% more fresh weight than ebb-and-flow subirrigation, and the subirrigated pots stayed wetter before each watering.

**The honest part:**
- With top watering, the probe reading depends on where the water lands. An outlet close to the probe makes the reading jump right after a dose, before the water spreads.
- Bottom watering wets the pot from below more evenly, but it is harder to give one pot a measured volume.

**What we learned / would change:** fix every outlet at the same distance from the probe, and add a check that the reading 2 hours after a dose matches the expected rise.

**Evidence:** phone photos Nov 17 (`2026-11-16-greenhouse-kit/pot1..pot9.jpg`); `irrigation_log.csv` and `sm_log.csv` around each P-06 dose.

## Q3. How did you calculate how much water each pot gets?

**Fact** (firmware `main.cpp` lines 119–121 and 388–400):
- **Target:** the middle of the pot's band.
- **Dose (mL)** = (target − reading) × **3.18 mL per point**, capped at 100 mL.
- **Valve time** = dose ÷ 18 mL/s (flow measured Oct 12: 90 mL in 5 s), capped at 30 s.
- **Wait:** 2 hours before the next decision (stabilisation time).
- **Guards:**
  - a reading below 10% counts as a probe fault and is not watered (added Nov 8 after P-01's false doses);
  - ADC range checks;
  - a pot is quarantined after 3 faults in a row.

**Example (real dose, `irrigation_log.csv`, Nov 6 09:35):** P-05 read 50.0% in the 50–60 band.
- Target 55.0, deficit 5.0 points.
- Dose = 5.0 × 3.18 = **16.0 mL**, valve open 0.89 s.

**The honest part:**
- Weighing the pot gave 388 g oven-dry and 662 g saturated, so **274 mL** of water covers the whole 0 to 100 scale. That is **2.74 mL per point**, not 3.18.
- So each dose is about 3.18 ÷ 2.74 = **1.16, about 16% too large**.
- In the example, 16.0 mL raises the pot by about 16.0 ÷ 2.74 = 5.8 points instead of 5.0: from 50.0 to about 55.8%. That is still inside the band, so the error is small near the band but grows with large deficits.
- The bands are fixed percentages of saturation, not based on the plant's measured water use.

**What we learned / would change:** set the factor from the weighed pot (2.74), and check each dose against the reading 2 hours later.

## Q4. Why a relative moisture scale instead of true volumetric water content?

**Fact:**
- Each probe is calibrated at two points, oven-dry soil = 0% (ADC 2483) and saturated soil = 100% (ADC 1120). P-03 and P-05 are shifted by an air test so all probes agree in air (`main.cpp` lines 101–106).
- **Conversion:** true VWC ≈ relative % × 274 mL ÷ 601 mL ≈ relative % × **0.456** (Chapter 3).

| Band | Relative scale | True VWC (about) |
|---|---|---|
| Low | 30 to 40% | 13.7 to 18.2% |
| Optimal | 50 to 60% | 22.8 to 27.4% |
| High | 70 to 80% | 31.9 to 36.5% |

**Why:** the relative scale is tied to our own soil, so every probe means the same thing, and it converts to VWC with one factor.

**The honest part:** after the D12 probe-supply fault (Nov 9), every probe read 8 to 31 points lower than before the fault. The calibration has not been re-checked since.

**What we'll do:** re-check 1 or 2 probes in air and in saturated soil after harvest, or report it as a limitation.

## Q5. Why didn't the plants grow?

**Fact:**
- At D20 every plant is still at the seed-leaf (cotyledon) stage, leaves about 1 cm, no true leaves (phone photos Nov 17).
- P-03 died (GPR 0.00 from D17). P-04 is weak.
- The canopy is under 0.5% of each pot's area. For 6 of 8 plants, the fitted growth curve levelled off at 0.14 to 0.25% of the pot area, with the fastest growth between D5 and D9 (`DATA/model_preview/fits.csv`).

**Possible causes, with what we have for each:**

| Cause | Evidence so far |
|---|---|
| Light | Pak choi grows best in full sun; heavier shading inhibited growth (Fadilah et al., 2022). Our noon frames are often dim (D20 12:42: exposure 10.9 ms). Shade cloth over P-01, P-04 and P-07 from D8 to D10. **Measure light at noon (lux) to confirm** |
| Small pot | 0.60 L; see Q1 (Poorter et al., 2012) |
| Transplanting | P-01, P-03 and P-06 got transplanted seedlings on D8, a week behind |
| Too wet (P-01) | P-01 has read above 89% since D11, far above its 30–40 band, after 7 false 100 mL doses |
| Hand watering and spraying early on | D1 to D4 hand watering; sprays D6, D7 and D10; misting D10 to D14 (event log) |

**The honest part:** we don't know the main cause yet. High (wettest) has the most canopy, so too much water alone doesn't explain it.

**What we'll do:** measure noon light at the current site and the proposed new site, get an agronomy opinion, and present the D40 plan (and relocation, if the panel agrees).

## Q6. Why didn't the treatments separate?

**Fact:** group averages of the noon soil reading (`growth_dataset.csv`):

| Day | Low (band 30–40) | Optimal (50–60) | High (70–80) |
|---|---|---|---|
| D1 | 59.8 | 84.3 | 98.1 |
| D8 (bands start) | 71.5 | 72.0 | 89.0 |
| D12 | 61.4 | 53.9 | 78.6 |
| D17 | 59.8 | 56.7 | 76.9 |
| D18 | 61.9 | 56.2 | 80.1 |

- High stayed in or near its band.
- Optimal reached its band from about D12.
- **Low never reached 30–40%.** From D12, Low and Optimal overlap.

**Why:**
- The controller can only **add** water. A pot above its band waits until it dries.
- The pots started wet, and drying was slow: Low fell from 71.5 to 57.5 between D8 and D16, about 14 points in 8 days. Seedlings this small use very little water.
- Water was added by hand: D1 to D4, sprays D6, D7 and D10, misting D10 to D14.
- P-01 received 7 false 100 mL doses (D10 to D11) and has stayed above 89% since.

**What we learned / would change:** start each pot at or below its band, by weighing it to the target water content before sowing, and allow no hand watering after D1.

**Evidence:** `growth_dataset.csv`, `sm_log.csv`, `irrigation_log.csv` (25 doses logged to Nov 17: P-01 3, P-02 3, P-03 1, P-04 1, P-05 9, P-06 3, P-08 5), event log.

## Q7. Nine plants and a six-term model: isn't that overfitting?

**Fact:** yes. Now 7 to 8 usable plants (P-03 dead, P-04 weak).

**Why it matters:** a regression needs many more plants than terms. Harrell (2015) gives a rule of thumb of roughly 10 to 20 observations per term (**verify the page before the slide**). With 8 plants, even one predictor is at the limit.

**What we changed:**
- **Main model:** weight = a + b × GPR at harvest, one predictor, evaluated by leave-one-plant-out.
- The six-term model is reported as **exploratory** only.
- Both are written into a protocol and committed to GitHub **before** harvest, the same way the growth-model protocol was (commit `1a4e050`, before the results in `3387aab`).

## Q8. Can we trust the GPR measurement?

**Fact:**
- The mask agrees with hand-labelled leaves at **IoU 0.64**; two people labelling the same leaves agree at **IoU 0.79** (Chapter 4; `GPR_VALIDATION/`).
- Average bias: **+0.04 percentage points** of pot area (mask comparison, Nov 16).
- Alternatives were tested and rejected:
  - a two-level mask: IoU 0.653, but bias +0.33;
  - ExG: IoU 0.165, because the rice-hull mulch reads as green.
- The phone photos on Nov 17 match what the masks counted.

**The honest part:**
- The labels were made by team members, on D12 and D13 frames.
- Blue (overcast) frames lose leaf pixels: D19 (blue/red 1.84) and D20 (1.57) read low and are flagged.

**What we changed:** from D21, a blue frame (blue/red above 1.25) is retaken at the next 10-minute try; the 12:50 try always writes.

## Q9. What about the missing and broken days?

**Fact:** every event is in `DATA/2026-11-17-run2-event-log.md`, with its source.

| Event | Handling |
|---|---|
| D2, D3 lost (power outage Oct 30–31) | Not filled in; left blank |
| D12 probe supply fault (Nov 9) | Readings blank from about 00:10 to 12:35. The D12 rows combine the 12:00 photo with the 12:42 soil readings (team decision) |
| D18 rows wiped by a git pull on the Pi (Nov 15, about 12:16) | Measured again from the saved noon frame on Nov 16 (`recover_day.py`). Git merges on the Pi are now blocked |
| D19 and D20 blue frames | Flagged; blue-frame retry added from D21 |
| D20 two captures (09:36 after a reboot, 12:42 retake) | Kept 12:42; the 09:36 set moved aside, not deleted. Catch-up limited to 12:00–12:55 |
| Probe readings jump 15 to 20 points together (from Nov 16 23:44) | Being checked as a wiring or supply fault; affected readings flagged |
| Pi restarts | 91 logged to Nov 17 (67 Pi-only). Most recent ones at :29–:30, when the hourly camera job ran; job turned off Nov 17 |
| Unlogged water | P-01: 7 false doses, 3 logged. P-09: about 90 mL by a wrong web button (D8). Both in the event log |

**Error log:** 5,948 entries; all but 2 are from Nov 9 (5,910 BMP_READ_FAIL, 27 SENSOR_RANGE, 9 POD_QUARANTINE). The other 2 are SENSOR_RANGE on Nov 17 08:44.

**What we changed:** backups twice a day, the git guard, health-check scripts, raw frames in GitHub with checksums (`DATA/agrisentry_data/frames/README.md`).

## Q10. Isn't treatment mixed up with position?

**Fact:** yes. Each group is one row of the grid: Low P-01 to P-03, Optimal P-04 to P-06, High P-07 to P-09. Any difference in light or temperature between rows is mixed with the treatment.

**Also:** the High row is at the edge, where outside greenery got into P-08 and P-09 (D13, D15; flagged).

**What we'd change:** randomise positions, or rotate the pots on a fixed schedule.

## Q11. You changed the capture code in the middle of the run?

**Fact:** yes, and each change is logged with its date:

| When | Change | Effect on the measurement |
|---|---|---|
| Nov 8 (D11) | Probe readings below 10% are treated as faults and not watered | Irrigation only |
| Nov 8 (D11) | Alignment reference re-based; a day isn't written if alignment is weak | Better pot positions |
| Nov 17 | Hourly camera job (`light_log`) turned off | None on the noon photo |
| Nov 17 | Catch-up capture only between 12:00 and 12:55 | Keeps every day in the noon window |
| Nov 17 (from D21) | Blue-frame retry | Chooses **when** in 12:00–12:50 the photo is taken; the GPR calculation is unchanged |

## Q12. Where is the pH?

**Fact:** the pH table (`DELIVERABLES/D2_uniform_environment/pH_table_template.csv`) is empty. The sensor (PH-4502C, `tools/ph4502c/`) arrives about Nov 19.

**Plan:**
- Measure the retained Day 0 soil and the tank water, 3 readings each, with temperature.
- The PH-4502C is a liquid probe, so soil is measured as a soil-and-water mix (**method to verify**).
- Pot pH at harvest, to avoid disturbing roots now.
- The table records that the Day 0 soil was measured on Nov 19 from the retained sample.

---

## Correction to the submitted manuscript (say it before they find it)

4.2.2, Chapter 5 and the abstract say Low was 7.5 points **below** Optimal at D12. The data show Low **61.4** and Optimal **53.9**: Low was higher, because of P-01. Without P-01, Low is 46.3, which is 7.6 below Optimal. This will be corrected in the revision.

## Questions they may also ask (answers to add)

- Why did you choose these three bands?
- How many plants will you harvest, and what if more die?
- What is the system's cost compared with the proposal?
- Why not extend to D40 from the start? Why not replant?
- How will you show the system "works" if the plants are small?
