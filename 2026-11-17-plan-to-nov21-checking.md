# Plan to the Project Checking: Tue Nov 17 to Sat Nov 21, 2026

**Written:** Nov 17, 2026 (D20), evening. Update this file as items are done (tick the boxes, add the time).

## 0. The checking

| Item | Detail |
|---|---|
| Date and time | **Sat, Nov 21, 2026, 1:30 to 4:30 PM** (shared block with group O_26; order not yet known, so be ready from 1:30) |
| Venue | Start at the **DCPE Conference Room**; setup at the **Bunzel greenhouse outside the PCB Lab** (expect the panel to walk to the pots) |
| Group code | B_26 |
| Panel | Dr. Luis Gerardo Cañete (chair), Engr. Andre Kimberly Trish D'Silva, Engr. Kenneth Carl Labarosa |
| Advisers | Engr. Alvin Joseph Macapagal (adviser), Engr. Linda Saavedra (assistant adviser) |
| Run day on Saturday | **D24** (D1 = Oct 29). The D24 noon capture (12:00 to 12:50) happens **before** the checking |

**Official Title:** "Computer Vision-Based Growth Monitoring and Yield Prediction for Pechay Under Differential Soil Moisture Treatments in a Greenhouse" (ensure all slides, documents, and scripts use this exact title; "AgriSentry" and "IoT irrigation system" have been removed).

## 1. What we are aiming for on Saturday

1. **Show what works, with evidence** (about 70% of the time): the system runs every day, every reading and dose is logged, the vision pipeline is validated, and the data is safe and traceable.
2. **Name the problems ourselves before the panel does** (about 30%): the stalled plants, the treatment bands, the data incidents and the known manuscript error, each with what we did about it.
3. **Bring a concrete proposal** for the remaining weeks (section 5), so the discussion ends on a plan, not on the problems.

**Data rule for every slide and answer:** every number comes from a file in the repo, as measured, with its flag if it has one. Nothing estimated or reconstructed is shown as measured. If a value is missing or invalid, the slide says so.

## 2. Deliverables: where each one stands

Percentages are a proposal for the team to agree on. The "basis" column says how each was counted, so the panel can check it.

| # | Deliverable | Now (Nov 17) | To add by Friday | Proposed % on Sat | Basis |
|---|---|---|---|---|---|
| 1 | Two-point calibration log; irrigation log | Calibration done; irrigation log running since D1 | Calibration re-check after the D12 supply fault (or state it as a limitation); dose count to D23 | 90% | only the post-D12 re-check is missing |
| 2 | Day 0 pH table; HSV values; `pot_rois.json` | HSV and ROI done; pH table empty | pH of the retained Day 0 soil and tank water (sensor arrives about Nov 19) | 70% now, 100% if pH is measured | 2 of 3 items done |
| 3 | 9 per-pot GPR time series; capture log; plots | D1 to D20 (D2, D3 lost) | Plots and table to D23; D19/D20 flagged | 73% | 22 of 30 planned days by D24 |
| 4 | Harvest table; scale check sheet | Not started (harvest after Saturday) | Scale check sheet filled (known mass, 3 readings) | 10% | scale check only |
| 5 to 6 | Regression model; LOOCV R² and MAE | Code ready; pre-harvest growth model run per protocol | Simplified-model protocol written (section 5) | 30% | code, protocol and pre-harvest test done; needs harvest weights |
| 7 | Error log; reliability summary | Logs running; summary text still at D8 | Reliability summary refreshed to D23 | 80% | logs complete; summary to refresh |

## 3. Day-by-day plan

Same rules every day:
- **Don't run anything on the Pi between 11:45 and 12:55.** On site, either finish before 11:45 or start after 12:55.
- No git on the Pi; no `capture_gpr.py` by hand; no ESP32 re-flash; no moving or replanting pots.
- Write the time of every physical action, then send it to Claude to log.
- After every pull or change: update HANDOFF.md and push.

### Tue Nov 17 (D20), tonight

- [x] Push the D20 fix logs (`bd5a152`).
- [ ] Push this plan (commands in section 8).
- [ ] Read this plan in the group chat and agree on the stance in section 5 (D40 extension first, replant as fallback).
- [ ] Send the message to Sir AJ (draft in Appendix A) and ask about the title.
- [ ] **Claude:** start the question-and-answer document (`DATA/2026-11-18-checking-qa-prep.md`): the 12 questions in section 4, each with the honest fact, the evidence and what we changed, with numbers and file references.

### Wed Nov 18 (D21)

**On site** (before 11:45 or after 12:55):
- [ ] `check_pi.bat`: D21 present, colour normal or retried by the cast guard.
- [ ] **Probe wiring check** (probe readings jump 15 to 20 points together since Nov 16 23:44):
  - photograph the probe power and ground wiring, connectors and the multiplexer board;
  - look for moisture, corrosion or a loose connector;
  - if a connector is loose, reseat it and write the time; change nothing else;
  - the next pull shows whether the jumps stop.
- [ ] **Scale check:** weigh one known mass 3 times on the 0.01 g scale; write the 3 readings in a scale check sheet.
- [ ] Phone photos of every pot from above, same angle as Nov 17.
- [ ] `pull_from_pi.bat` after 12:55, then send Claude the folder name.

**Claude:**
- [ ] Copy the pull into the repo; update the data log, event log and HANDOFF.md; give push commands.
- [ ] Deliverable evidence: GPR plots to D21 (D19, D20 flagged), the predictor table and correlation matrix (D, GPR, SM, with invalid SM flagged), reliability summary to D21, `DELIVERABLES/README.md` with the table in section 2.
- [ ] Check the literature for the pots, top-watering, pechay growing-conditions and overfitting answers; only papers that were read get cited.
- [ ] Finish the question-and-answer document.
- [ ] Errata list for the submitted manuscript, starting with the D12 group order (the text says Low < Medium; the data has Low 61.4 > Medium 53.9 because of P-01; without P-01, Low is 46.3).

### Thu Nov 19 (D22)

**On site:**
- [ ] `check_pi.bat`.
- [ ] **pH (when the sensor arrives):**
  - set it up and check it as its manual says (buffer solutions if included);
  - measure the **retained Day 0 soil** and the **tank water**, 3 readings each, with the temperature, into `DELIVERABLES/D2_uniform_environment/pH_table_template.csv`;
  - don't push the sensor into the experiment pots now; the seedlings' roots are about 1 cm from the surface, and pot pH can be measured at harvest;
  - write on the table that the Day 0 soil was measured on Nov 19 from the retained sample.
- [ ] `pull_from_pi.bat`.

**Team:**
- [ ] Read the question-and-answer document and rewrite each answer in your own words, at most 3 sentences each.
- [ ] Follow up with Sir AJ if he hasn't answered.

**Claude:**
- [ ] Slide outline and draft (few words, visuals, image placeholders): system, what works, data to D22, problems and fixes, proposal.
- [ ] One backup slide per question in section 4.
- [ ] Log the pH readings and pull; update HANDOFF.md; push commands.

### Fri Nov 20 (D23)

**On site:**
- [ ] After 12:55: `check_pi.bat`, then `pull_from_pi.bat`.
- [ ] Tidy the greenhouse for the visit: pot labels visible, cables tied, no tools or stray plants in the camera view. Don't move any pot.
- [ ] Take screenshots for an offline backup: `check_pi` output, the latest frame with the mask overlay, the soil and dose logs, and the HANDOFF summary.

**Claude:**
- [ ] Update the slides and the deliverables table with the D23 numbers.
- [ ] **Mock panel (evening):** Claude asks the 12 questions plus questions you haven't seen; you answer by text or voice; Claude marks which answers need work.

**Team:**
- [ ] Final slides; send the file to Sir AJ if he wants to see it first.
- [ ] Charge laptops and phones; download the slides and screenshots for offline use (the greenhouse internet is slow).

### Sat Nov 21 (D24): checking day

| Time | Do |
|---|---|
| Before 11:45 | Arrive; `check_pi.bat`; look over the pots and the camera housing |
| 11:45 to 12:55 | **Hands off the Pi.** The D24 noon capture runs |
| After 12:55 | `check_pi.bat` (D24 present and colour); optional `pull_from_pi.bat`; screenshots of D24 |
| 13:15 | The backup runs on the Pi by itself; nothing to do |
| 13:30 | Checking starts (DCPE Conference Room, then the greenhouse) |
| During | One person writes down every comment **word for word** with who said it |
| After | Send the notes to Claude; Claude turns them into revision points and logs them |

**At the greenhouse, during the checking:**
- Show the pots, probes, valves, camera housing and controller box; then on the laptop: the health check, the latest frame with the mask, and the logs.
- **Don't trigger a manual watering or a manual capture.** A manual dose adds water to a treatment pot and breaks the experiment. If asked to see a valve fire, explain this, and show the logged doses (and a bench-test video if we have one).

## 4. Questions to prepare (no names yet)

Answer each one in three parts: **the honest fact, with a number; why we chose it, with evidence; what we learned or changed.** Full answers go in the question-and-answer document.

| # | Likely question | Core of the answer |
|---|---|---|
| 1 | Why pots, not plots? | One probe and one valve per pot gives per-plant control, as in Zamora et al. (2025). Trade-off: small pots restrict roots and growth (Poorter et al., 2012). Stated as a limitation |
| 2 | Why top watering, not bottom? | Drip design inherited from Zamora et al. (2025), one valve per pot; the probe reads the upper root zone where the water lands. Honest: bottom watering wets the root zone more evenly; emitter position matters (P-06) |
| 3 | How was the dose calculated? | Dose = deficit × 3.18 mL per point. Weighing gave 2.74 mL per point (274 mL from oven-dry to saturated), so the firmware is about 16% high. Example: a pot at 50% gets 5 × 3.18 = 15.9 mL and rises about 5.9 points to 55.9%, still in the band |
| 4 | Why a relative moisture scale? | Two-point calibration per probe; true VWC ≈ 0.456 × the relative value. Already in the revision letter and limitations |
| 5 | Why didn't the plants grow? | Seed-leaf stage at D20 (photos). Possible factors: light, pot size, the soil mix, transplanting, waterlogging (P-01). Needs literature on pechay requirements |
| 6 | Why didn't the treatments separate? | The controller can only add water; the pots started wet; hand watering D1 to D4. Lesson: start every pot at or below its band |
| 7 | Nine plants and six terms: overfitting? | Agree. With 7 to 8 plants the main model becomes weight vs GPR, written down before harvest; the six-term model is exploratory. About 10 to 15 units per predictor (Harrell, 2015) |
| 8 | Can we trust the GPR? | IoU 0.63 against hand labels, bias +0.04 pp; phone photos match the masks. Honest: validation frames are from the trial run, labelled by the team |
| 9 | What about the missing or broken days? | The event log: D2 and D3 power loss; D18 wiped by git and recovered from the saved frame; D19 and D20 blue frames; D20 duplicate resolved; probe faults. Each logged with its handling and fix |
| 10 | Treatment mixed up with position? | Yes: each group is one row. Limitation; randomise positions next time |
| 11 | You changed the code mid-run? | The colour guard only chooses when, inside the 12:00 to 12:50 window, the photo is taken; the measurement is unchanged. Logged |
| 12 | Where is the pH? | The Day 0 soil and tank water measured on Nov 19 to 20 (if the sensor arrives); pot pH at harvest |
| 13 | Why not extend capture to 12:00–16:00? | Diurnal leaf droop/movement + moving Bunzel building shadows after 13:00 break time-series consistency. Solar noon ($\pm 30\text{ min}$) + $V=73$ exposure loop keeps geometry & lighting comparable (Patrignani & Ochsner, 2015) |
| 14 | Why not use the LED capture light? | Switching the LED array caused $>1.5\text{ A}$ current spikes and voltage sag that brownout-reset the Pi; at $136\text{ cm}$ in $20\text{k–}50\text{k lux}$ daylight its optical gain was negligible. Replaced by $V=73$ software normalization |
| 15 | Why manual misting/spraying in Low? | Root-probe depth gap: capacitive probes sit $4\text{–}8\text{ cm}$ deep while cotyledon roots are $\sim 5\text{ mm}$ in a drying $1\text{ cm}$ crust. Survival misting logged in `event_log.md`/`field_log.csv` and separated from `irrigation_log.csv` |

## 5. What we propose to the panel

**Option 1 (preferred if panel accepts small plants): extend the current run to D40.**
- Harvest on **Dec 7 (D40)** instead of Nov 27 (D30); the last checking is Dec 12.
- P-03 is dead and P-04 is weak: harvest P-04 at D30 (Nov 27) if it is still alive, so it still gives a weight.
- With 7 to 8 plants, the main yield model is **weight = a + b × GPR**; the six-term model is reported as exploratory. This is written and committed before harvest, like the growth-model protocol.
- The pre-harvest growth model result (does not beat persistence, canopy stalled) is reported as a result.

**Option 2 (if the panel asks for a replant): swap in the Nov 20 backup batch on D7 (`2026-11-19-replant-plan.md`).**
- Backup batch of 15–20 pots (improved `3:1:1` soil mix, pH-checked) sown **Thu Nov 20 (New D1)** off-rig and watered by weight.
- Harvest Run 2 on **Wed Nov 26 (New D7)**, swap the 9 most uniform seedlings into the rig, turn `bands-on` on **Thu Nov 27 (D8)**, and run official captures through **Dec 19 (D30)** (2nd checking Dec 7–13 falls on D18–D24).

Either way, the current plants stay in place and keep being logged through Nov 21.

## 5b. Briefing Slide Flow for Kent's PPT (8–10 min)

*Approach: Lead 70% with verified engineering proof, name the plant status & diagnostics proactively (30%) as findings rather than apologies, and end on Option 1 vs Option 2.*

1. **Slide 1 — Title & Decoupled Dual-Architecture (1 min):** Official title; diagram of ESP32-S3 (9 probes via MUX, BMP388, 12 relays, 4 safety guards) $\leftrightarrow$ UART $\leftrightarrow$ Pi Zero 2 W (Camera Module 3 IMX708 at $136\text{ cm}$, $V=73$ normalization).
2. **Slide 2 — Deliverables Verification Matrix (4 mins):** Table I deliverables (D1–D7) mapped directly to live repo files (`irrigation_log.csv`, `pot_rois.json`, `growth_dataset.csv` D1–D22, `frames/`, `analyze_yield.py`, `power_log.csv`, 36-image GPR validation $\text{IoU}=0.630, \text{MAE}=0.28\text{ pp}$).
3. **Slide 3 — Plant Growth Progress & Diagnostics (2 mins):** Proactive summary: 7/9 alive at cotyledon stage (`0.02%–0.42%` `cell_gpr` on sunny D22); diagnosed causes: (a) seasonal solar azimuth shift between the two Bunzel buildings shortening direct sun, (b) $26.7\%$ alkaline CRH in `8:4:3` (vs `3:1:1` / $5.5\text{–}6.5$ target), (c) $0.60\text{ L}$ pot volume (Poorter et al., 2012), and (d) D1–D4 wet start + electrical shifts logged transparently. *(Keep Q13–Q15 defenses in backup slides).*
4. **Slide 4 — Forward Proposal (2 mins):** Option 1 (extend Run 2 to D40 + 1-predictor LOOCV) vs. Option 2 (Nov 20 backup batch swap on Nov 26).

## 6. Not doing before the checking

- No replanting or moving pots without a written team decision.
- No firmware change, no re-flash.
- No editing of measured values. Problems are flagged, not fixed in the numbers.

## 7. Open items

- [ ] Which title is official
- [ ] Sir AJ's answer on Option 1 vs Option 2
- [ ] Our group's time slot within 1:30 to 4:30
- [ ] Cause of the probe jumps (after the Wednesday check)
- [ ] Why the Pi rebooted on Nov 17 at about 09:31

## 8. Push tonight

In the `THESIS` folder:

```
git add 2026-11-17-plan-to-nov21-checking.md HANDOFF.md
git commit -m "Plan to the Nov 21 project checking (Sat 1:30 PM, D24)"
git push
```

---

## Appendix A. Draft message to Sir AJ

> Good evening, Sir AJ. This is Kent from Group B. A short update before our project checking on Saturday (Nov 21, 1:30 PM):
>
> 1. The system has run every day since sowing on Oct 29: daily noon photos and soil readings for D1 to D20 (D2 and D3 lost to the power outage), and every dose logged.
> 2. The plants are still at the seed-leaf stage at D20, with leaves about 1 cm. P-03 has died and P-04 is weak, so we have 7 to 8 usable plants.
> 3. We ran the pre-harvest growth model from our Nov 9 logbook plan, with the rules committed before the run. It does not beat a "no change" forecast, because the canopy stopped growing. We will report this as it is.
> 4. Our proposal: extend the run to D40 (harvest Dec 7) instead of replanting. With 7 to 8 plants we would make the main yield model weight vs GPR only and report the larger model as exploratory, written down before harvest. If the panel prefers a replant, our fallback is to transplant older seedlings on Nov 22 and harvest by Dec 9.
>
> Which option would you support, so we can present it on Saturday?
>
> Thank you, Sir.
