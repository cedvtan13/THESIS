# Team notes: Oct 28, 2026 (D23)

What we found from the data, what we plan to do, and what each slide in today's deck says.
Deck: "Progress Report – Oct 28, 2026" (https://www.canva.com/d/Toa08xJjBmFmAnk).
Adviser meeting today, 10:30 am.

---

## 1. Where we are

- **Day 23 of 30.** Harvest is planned for D30 (Nov 4). 1st checking is in the 1st week of November; 2nd checking is Nov 23–28.
- **Data collection is complete:** D8–D22, 135 of 135 rows (9 pots × 15 days). Raw noon frames have been saved since D12.
- **Automatic watering works:** 18 doses delivered (351 mL). Each one fired right at the bottom of the pot's moisture band.
- **The groups are in the right order now:** low 52%, optimal 67%, high 76% (average from Oct 25 on).
- **Hardware tests (Oct 21):** every relay clicks and works. Flow is 18 mL/s on all 9 valves (90 mL in 5 s), which matches the firmware.
- **Not yet done:** the sensor check run 3 times (repeatability).

---

## 2. Problems we found

### Problem 1: the plants are growing slowly, likely from low light
- Pot-area GPR (see the glossary) barely rose from D12 to D21. The seedlings still have only a few true leaves.
- The stems are long and thin, and almost all lean the same way, toward the brighter side. That usually means not enough light from above.
- Noon light varies about 7× between days. D9, D13 and D18 were the darkest (the camera needed 46–52 ms exposure; on bright days it needs 8–10 ms).
- **Why it matters:** if all 9 plants stay tiny, their harvest weights will be similar, and the yield model will have little to learn from.
- **Plan:** no grow light. Instead, log light every hour using the camera (no new hardware; the exposure time works as a light meter) and flag dark days in the dataset.

### Problem 2: leaning plants fall outside the pot circle
- The camera measures GPR inside a circle over each pot's soil. Plants that lean past the rim drop out of it.
- The pot circle read 0 for P-05 (6 days), P-07 (6 days) and P-01 (3 days), but the plants are alive.
- **Fix:** a new measure, **pot-area GPR**. Each pot gets the area of the image nearest to it, up to 13 cm out, with no overlap between pots. Leaning leaves stay in their own pot's area. It's recomputed from the saved frames, so it exists from D12 on (no frames before D12).
- **Leaf angle:** GPR measures leaf area as seen from above. A tilted leaf looks smaller, but all our plants lean similarly, so the regression model absorbs it. We list it as a limitation.
- **Fallen leaf:** a leaf lay in P-06's area from about D16 to D21 and inflated its value. It was removed on Oct 27. Those days are flagged.

### Problem 3: the treatments are only half in place
- **Low group (30–40%):** only P-02 got into its band. P-01 and P-03 are still at about 55%.
- **P-06 (optimal, 50–60%):** it has stayed at 86–100% for 11 days while the pots next to it dried. Possible causes: a dripping valve, water in the saucer, or a faulty probe. **We need to check this at the greenhouse.**
- The soil started out saturated, which is why the low group took so long to dry.

### Other events (all logged in the field log)
- **Oct 21, camera knocked:** the image shifted 209 px. Re-aimed by hand and the circles refitted the same morning, before the noon capture.
- **Oct 27, camera drift:** the camera had drifted 15 px since D16. Each circle was shifted to match; the old circles are backed up.
- **Pi power cuts:** 17 so far, mostly when mains is plugged or unplugged, or the cable gets pulled. Only one capture was affected (D16 ran at 12:10 instead of 12:00).
- **Plastic sheet:** a sheet in the camera view was pulled back on Oct 27.

---

## 3. If we replant (decision for sir AJ)

A full 30-day run from scratch can't finish before the 2nd checking (sowing today puts D30 on Nov 26). A shorter run fits:

| Date | Day | What happens |
|---|---|---|
| Oct 29 | D1 | Sow 20–30 seeds in trays, in the brightest spot |
| Nov 4 | — | Harvest the current run (data for the 1st checking) |
| Nov 5 | D8 | Transplant the 9 most uniform seedlings into the same pots; logging starts |
| Nov 19–20 | D22–D23 | Harvest run 2; run the model the same day |
| Nov 23–28 | — | 2nd checking |

Sowing a backup tray costs almost nothing. If we don't replant, we just don't use it.

**What we'd change next time:**
- **Light:** no grow light. Log light every hour, flag dark days, and make sure the cover doesn't shade the pots.
- **Soil:** reuse the pots. Mix all the soil, then let it air-dry until it's moist, not saturated, so the treatments start within days.
- **Seedlings:** transplant the 9 most uniform, and take a photo record at transplant.
- **Camera:** rigid mount, pot-area GPR from day 1, a daily drift check, and save every frame.
- **Valves and probes:** a leak test (P-06), the probe-mapping test, and the sensor check ×3 before D1.
- **Power and site:** secure the Pi cable, and keep weeds, leaves and plastic out of view.

---

## 4. Reliability tests to collect (to show the panel the system works)

| Test | Number we report | What it proves |
|---|---|---|
| Sensor check ×3, and probes left alone for 1 hour | ± counts per probe | Sensors give steady readings (repeatability) |
| Soil sample next to a probe, weighed, oven-dried, weighed again | Probe % vs true moisture | Sensor **accuracy** |
| All 9 probes in one batch of soil | Spread between probes | Probes agree |
| Command a dose, catch it in a cup, 3× per valve | mL asked vs mL delivered | Dose accuracy |
| Pump off, valves closed for 1 hour | Drips yes/no | No leaks |
| Relays switched once each | Pass/fail | Done ✓ |
| GPR vs hand labels | Bias, error, overlap | Done ✓ (repeat on bigger plants) |
| 5 captures in a row | GPR variation | Camera repeatability |
| Green card of known size on the soil | Measured vs true area | Size accuracy |
| Logs | Captures done vs scheduled, power cuts, watering responses | Overall reliability |
| Weigh a known mass 3× | Error in grams | Harvest scale is trustworthy |

---

## 5. Questions for sir AJ (slide 11)

1. Should we replant for the 2nd checking?
2. If we replant, is a ~3-week run (data D8–D22) acceptable?
3. Which harvest day for the current run and the 1st checking: D26 (Oct 31) or D30 (Nov 4)?
4. Can we use pot-area GPR as the main growth measure, since the plants lean?
5. No grow light: is logging dark days with the camera acceptable?
6. How was the 30–40% band chosen, given that 0% = oven-dried soil and 100% = saturated soil?

---

## 6. What each slide says (talking points)

1. **Title.** Oct 28, Day 23.
2. **Since Oct 22.** Three things working (data complete, 18 automatic doses, camera drift fixed) and three problems (slow growth, treatments partial, P-06 stuck wet). Also 4 more Pi power cuts, with no capture lost.
3. **Data D8–D22.** Top row: soil moisture per group, with the target band shaded and the doses marked. Bottom row: pot-area GPR. The groups are in the right order, but the low group isn't in band yet. GPR is barely rising. P-06's spike from D16 is the fallen leaf.
4. **Problem 1: slow growth, low light.** The bars show noon light per day as a % of the brightest day; the dark bars are the darkest days. Message: growth is flat, light varies 7×, and the stems are leggy. Plan: log light with the camera.
5. **Problem 2: leaning plants.** Left: each pot's own area (yellow) on the D21 photo. Right: P-05 leaning out of its circle. The new pot-area GPR fixes the zero readings.
6. **Problem 3: treatments.** Bars show how much of the time each pot was inside its band. Only P-02 in the low group made it. P-06 is stuck around 87%. Watering itself works.
7. **Camera drift.** Before: the circles sat about 15 px off the pots. After: shifted per pot on Oct 27, before the D22 capture.
8. **If we replant: timeline.** Sow Oct 29, transplant Nov 5, harvest Nov 19–20, before the 2nd checking.
9. **If we replant: what we'd change.** Light, soil, seedlings, camera, valves and probes, power and site. Same rig, no new hardware.
10. **Reliability tests.** The two columns from section 4.
11. **Requests for sir AJ.** The six questions above.
12. **Summary.** Seven one-line points.

---

## 7. Words to know

- **GPR (Green Pixel Ratio):** the percentage of a pot's area that the camera counts as green leaf.
- **pp (percentage points):** a difference between two percentages. For example, 1.50% vs 1.78% is 0.28 pp apart.
- **Pot circle:** the original measurement circle over each pot's soil (13 cm across).
- **Pot-area GPR:** the new measure. Each pot gets the part of the image nearest to it, up to 13 cm out, with no overlap between pots.
- **Band:** the target soil-moisture range for each group (low 30–40%, optimal 50–60%, high 70–80%). 0% = oven-dried soil, 100% = saturated soil.
- **LOOCV:** leave-one-plant-out testing. The model is trained on 8 plants and predicts the 9th, repeated 9 times. It shows how well the model predicts a plant it never saw.
- **IoU:** how much two leaf outlines overlap (1 = identical, 0 = no overlap). Used in the GPR validation.

---

## 8. To do

- [ ] Ask sir AJ the six questions; write down his answers
- [ ] If replanting: sow the backup tray today or tomorrow
- [ ] At the greenhouse: check P-06 (soil feel, saucer water, valve drip over 1 hour)
- [ ] Phone lux reading at noon: inside at pot level vs outside
- [ ] Run the sensor check 3 times (after 12:50)
- [ ] Next hotspot session: add D23 to pot-area GPR, clean the P-06 frames, set up hourly light logging
