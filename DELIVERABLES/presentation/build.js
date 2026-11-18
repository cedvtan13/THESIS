const pptxgen = require("pptxgenjs");
const path = require("path");
const D = __dirname;
const img = (f) => path.join(D, f);

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.title = "Computer Vision-Based Growth Monitoring and Yield Prediction for Pechay Under Differential Soil Moisture Treatments in a Greenhouse — Run 2 Progress Check";
pres.author = "Rey Adag, Kent Godinez, Cedric Tan";
pres.theme = { headFontFace: "Arial", bodyFontFace: "Arial" };

const DARK = "1F3D2B", GREEN = "2E7D4F", MOSS = "8DB580", TINT = "EEF5EC", INK = "1C1C1C",
  MUTED = "5B6660", LINE = "D5DDD3", WHITE = "FFFFFF", AMBER = "B26A00";
const GRP = { Low: "D9622B", Optimal: "2A78D6", High: "178F64" };
const HF = "Arial", BF = "Arial";
const W = 13.333;

let n = 0;
function content(title, badge) {
  const s = pres.addSlide();
  n++;
  s.background = { color: WHITE };
  s.addText(title, { x: 0.6, y: 0.35, w: 10.9, h: 0.8, fontFace: HF, fontSize: 32, bold: true, color: DARK,
    margin: 0, valign: "middle", isTextBox: true });
  if (badge) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 11.55, y: 0.45, w: 1.2, h: 0.6, rectRadius: 0.3,
      fill: { color: TINT }, line: { color: TINT } });
    s.addText(badge, { x: 11.55, y: 0.45, w: 1.2, h: 0.6, fontFace: BF, fontSize: 14, bold: true, color: GREEN,
      align: "center", valign: "middle", margin: 0, isTextBox: true });
  }
  s.addText("Pechay Growth & Yield Monitoring · Run 2 · Progress Check", { x: 0.6, y: 7.0, w: 8, h: 0.3, fontFace: BF,
    fontSize: 10, color: MUTED, margin: 0, isTextBox: true });
  s.addText(String(n), { x: 12.13, y: 7.0, w: 0.6, h: 0.3, fontFace: BF, fontSize: 10, color: MUTED, align: "right",
    margin: 0, isTextBox: true });
  return s;
}
function card(s, x, y, w, h, fill = TINT) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: fill } });
}
function stat(s, x, y, w, big, label, color = GREEN) {
  s.addText(big, { x, y, w, h: 0.9, fontFace: HF, fontSize: 40, bold: true, color, margin: 0, valign: "bottom", isTextBox: true });
  s.addText(label, { x, y: y + 0.95, w, h: 0.75, fontFace: BF, fontSize: 14, color: INK, margin: 0, valign: "top", isTextBox: true });
}
function lines(arr, size = 15) {
  // arr: strings or [bold, rest]
  return arr.map((t, i) => {
    const last = i === arr.length - 1;
    if (Array.isArray(t)) return [
      { text: t[0], options: { bold: true, color: INK, fontSize: size } },
      { text: t[1], options: { color: INK, fontSize: size, breakLine: !last } },
    ];
    return [{ text: t, options: { color: INK, fontSize: size, breakLine: !last } }];
  }).flat();
}
function bullets(arr, size = 15) {
  return arr.map((t, i) => {
    const last = i === arr.length - 1;
    const o = { bullet: true, color: INK, fontSize: size, paraSpaceAfter: 6, breakLine: !last };
    if (Array.isArray(t)) return [{ text: t[0], options: { ...o, bold: true, breakLine: false } },
      { text: t[1], options: { color: INK, fontSize: size, breakLine: !last } }];
    return [{ text: t, options: o }];
  }).flat();
}

// 1. Title -------------------------------------------------------------
{
  const s = pres.addSlide(); n++;
  s.background = { color: DARK };
  s.addImage({ path: img("d08raw.jpg"), x: 7.83, y: 0, w: 5.5, h: 5.5, altText: "Top view of the 9 pots, D8 noon" });
  s.addText("Computer Vision-Based Growth Monitoring and Yield Prediction for Pechay", { x: 0.7, y: 1.2, w: 6.8, h: 1.0, fontFace: HF, fontSize: 32, bold: true, color: WHITE, margin: 0, isTextBox: true });
  s.addText("Under Differential Soil Moisture Treatments in a Greenhouse", { x: 0.7, y: 2.3, w: 6.6, h: 1.0,
    fontFace: BF, fontSize: 20, color: "D6E6D2", margin: 0, isTextBox: true });
  s.addText("Run 2 progress check · Day 8 of 30 · November 5, 2026", { x: 0.7, y: 3.5, w: 6.8, h: 0.5,
    fontFace: BF, fontSize: 16, bold: true, color: MOSS, margin: 0, isTextBox: true });
  s.addText([
    { text: "Rey Adag · Kent Godinez · Cedric Tan", options: { breakLine: true } },
    { text: "Adviser: Engr. Alvin Joseph Macapagal" },
  ], { x: 0.7, y: 5.6, w: 7, h: 0.9, fontFace: BF, fontSize: 15, color: WHITE, margin: 0, isTextBox: true });
  s.addText("D8 noon photo, all 9 pots", { x: 7.83, y: 5.6, w: 5.2, h: 0.4, fontFace: BF, fontSize: 11, color: "B8CCB4",
    align: "right", margin: 0, isTextBox: true });
  s.addNotes("Start with the rig itself. This deck is backup for the demo: use it to show data the live screen cannot.");
}

// 2. At a glance --------------------------------------------------------
{
  const s = content("The experiment at a glance");
  const groups = [["Low", "P-01 to P-03", "30–40 %"], ["Optimal", "P-04 to P-06", "50–60 %"], ["High", "P-07 to P-09", "70–80 %"]];
  s.addText("3 moisture groups × 3 pots", { x: 0.6, y: 1.4, w: 5.6, h: 0.4, fontFace: BF, fontSize: 18, bold: true, color: DARK, margin: 0, isTextBox: true });
  groups.forEach(([g, pots, band], i) => {
    const y = 1.95 + i * 0.95;
    card(s, 0.6, y, 5.6, 0.8);
    s.addShape(pres.shapes.OVAL, { x: 0.8, y: y + 0.2, w: 0.4, h: 0.4, fill: { color: GRP[g] }, line: { color: GRP[g] } });
    s.addText(g, { x: 1.4, y, w: 1.6, h: 0.8, fontFace: BF, fontSize: 17, bold: true, color: INK, valign: "middle", margin: 0, isTextBox: true });
    s.addText(pots, { x: 3.0, y, w: 1.7, h: 0.8, fontFace: BF, fontSize: 15, color: INK, valign: "middle", margin: 0, isTextBox: true });
    s.addText(band, { x: 4.7, y, w: 1.3, h: 0.8, fontFace: BF, fontSize: 17, bold: true, color: GRP[g], align: "right", valign: "middle", margin: 0, isTextBox: true });
  });
  s.addText("Two boards", { x: 0.6, y: 4.95, w: 5.6, h: 0.4, fontFace: BF, fontSize: 18, bold: true, color: DARK, margin: 0, isTextBox: true });
  s.addText(lines([["ESP32-S3: ", "9 soil probes, 9 valves. Waters each pot on its own, without the Pi."],
    ["Pi Zero 2 W: ", "Camera Module 3. Noon photo, green pixel ratio (GPR), all logs."]], 15),
    { x: 0.6, y: 5.4, w: 5.6, h: 1.3, fontFace: BF, margin: 0, valign: "top", paraSpaceAfter: 6, isTextBox: true });

  // timeline
  s.addText("Timeline", { x: 7.0, y: 1.4, w: 5.7, h: 0.4, fontFace: BF, fontSize: 18, bold: true, color: DARK, margin: 0, isTextBox: true });
  const tl = [["D1 · Oct 29", "Sown. Germination mode: all pots 50–60 %", MUTED],
    ["D8 · Nov 5 (today)", "Transplants into empty pots, then treatment bands ON at 11:44", GREEN],
    ["D9 · Nov 6", "Full shade cloth over all 9 pots", MUTED],
    ["D30 · Nov 27", "Harvest, weigh, fit and test the yield model", DARK]];
  s.addShape(pres.shapes.LINE, { x: 7.25, y: 2.15, w: 0, h: 4.1, line: { color: LINE, width: 2 } });
  tl.forEach(([when, what, col], i) => {
    const y = 1.95 + i * 1.15;
    s.addShape(pres.shapes.OVAL, { x: 7.1, y: y + 0.08, w: 0.3, h: 0.3, fill: { color: col }, line: { color: WHITE, width: 2 } });
    s.addText(when, { x: 7.6, y, w: 5.1, h: 0.45, fontFace: BF, fontSize: 16, bold: true, color: col, margin: 0, valign: "middle", isTextBox: true });
    s.addText(what, { x: 7.6, y: y + 0.45, w: 5.1, h: 0.6, fontFace: BF, fontSize: 14, color: INK, margin: 0, valign: "top", isTextBox: true });
  });
}

// 3. Calibration ------------------------------------------------------------
{
  const s = content("Soil moisture calibration: two points", "D1");
  card(s, 0.6, 1.45, 3.9, 2.3);
  s.addText("0 % = dry", { x: 0.85, y: 1.6, w: 3.4, h: 0.5, fontFace: BF, fontSize: 20, bold: true, color: GRP.Low, margin: 0, isTextBox: true });
  s.addText(lines(["Soil mix oven-dried at 150 °C for 6 h", "Reading: dryADC = 2483"], 15),
    { x: 0.85, y: 2.15, w: 3.4, h: 1.4, fontFace: BF, margin: 0, valign: "top", paraSpaceAfter: 4, isTextBox: true });
  card(s, 4.75, 1.45, 3.9, 2.3);
  s.addText("100 % = wet", { x: 5.0, y: 1.6, w: 3.4, h: 0.5, fontFace: BF, fontSize: 20, bold: true, color: GRP.Optimal, margin: 0, isTextBox: true });
  s.addText(lines(["The same soil, fully saturated", "Reading: wetADC = 1120"], 15),
    { x: 5.0, y: 2.15, w: 3.4, h: 1.4, fontFace: BF, margin: 0, valign: "top", paraSpaceAfter: 4, isTextBox: true });
  s.addText("Done Sept 18, 2026 by Cedric, with the same soil mix as the pots", { x: 0.6, y: 3.9, w: 8.05, h: 0.4,
    fontFace: BF, fontSize: 14, italic: true, color: MUTED, margin: 0, isTextBox: true });
  card(s, 0.6, 4.45, 8.05, 1.1, "F4F6F4");
  s.addText("moisture % = (dryADC − reading) ÷ (dryADC − wetADC) × 100", { x: 0.85, y: 4.45, w: 7.6, h: 1.1,
    fontFace: "Courier New", fontSize: 17, bold: true, color: DARK, valign: "middle", margin: 0, isTextBox: true });
  s.addText([
    { text: "Relative moisture, not true volumetric water content (VWC). ", options: { bold: true, color: AMBER } },
    { text: "The bands (30–40, 50–60, 70–80 %) are on this oven-dry-to-saturated scale.", options: { color: INK } },
  ], { x: 0.6, y: 5.75, w: 8.05, h: 0.9, fontFace: BF, fontSize: 15, margin: 0, valign: "top", isTextBox: true });

  s.addText("Air test per probe (Oct 28)", { x: 9.0, y: 1.45, w: 3.75, h: 0.4, fontFace: BF, fontSize: 16, bold: true, color: DARK, margin: 0, isTextBox: true });
  const rows = [
    [{ text: "Probe", options: { bold: true } }, { text: "In air", options: { bold: true } }, { text: "Offset", options: { bold: true } }],
    ["7 probes", "4.1–7.0 %", "none"], ["P-03", "13.5 %", "−103"], ["P-05", "11.4 %", "−75"]];
  s.addTable(rows, { x: 9.0, y: 1.95, w: 3.75, colW: [1.35, 1.25, 1.15], fontFace: BF, fontSize: 14, color: INK,
    border: { type: "solid", pt: 0.75, color: LINE }, fill: { color: WHITE }, rowH: 0.45 });
  s.addText("P-03 and P-05 read wetter than the others in air, so both of their points were shifted by the same count. The span (1363 counts) is the same for all 9 probes.",
    { x: 9.0, y: 4.0, w: 3.75, h: 1.6, fontFace: BF, fontSize: 14, color: INK, margin: 0, valign: "top", isTextBox: true });
  s.addText("Log: DELIVERABLES/D1_calibration_and_irrigation/calibration_log.md", { x: 9.0, y: 5.75, w: 3.75, h: 0.8,
    fontFace: BF, fontSize: 11, color: MUTED, margin: 0, valign: "top", isTextBox: true });
}

// 4. Actuators --------------------------------------------------------------
{
  const s = content("Actuators: how much water each valve gives", "D1");
  stat(s, 0.6, 1.35, 3.0, "18 mL/s", "Flow per valve, measured on all 9 (90 mL in 5 s, Oct 12)");
  stat(s, 3.9, 1.35, 3.0, "3.18 mL", "Water per 1 % below the band's middle");
  stat(s, 7.2, 1.35, 2.5, "0", "Sensor or valve faults, D1–D8");
  s.addText("Safety limits in the firmware", { x: 0.6, y: 3.35, w: 6, h: 0.4, fontFace: BF, fontSize: 17, bold: true, color: DARK, margin: 0, isTextBox: true });
  const lim = [["100 mL", "most water in one dose"], ["30 s", "longest a valve can stay open"], ["2 h", "wait before the same pot is dosed again"], ["3 bad readings", "in a row: that pot's watering stops (quarantine)"]];
  lim.forEach(([a, b], i) => {
    const x = 0.6 + (i % 2) * 4.6, y = 3.85 + Math.floor(i / 2) * 1.2;
    card(s, x, y, 4.4, 1.0);
    s.addText(a, { x: x + 0.2, y, w: 1.75, h: 1.0, fontFace: BF, fontSize: 18, bold: true, color: GREEN, valign: "middle", margin: 0, isTextBox: true });
    s.addText(b, { x: x + 1.95, y, w: 2.3, h: 1.0, fontFace: BF, fontSize: 14, color: INK, valign: "middle", margin: 0, isTextBox: true });
  });
  card(s, 9.95, 1.35, 2.8, 5.35, "F4F6F4");
  s.addText("Example: P-02, Nov 5, 11:25", { x: 10.15, y: 1.5, w: 2.45, h: 0.7, fontFace: BF, fontSize: 15, bold: true, color: DARK, margin: 0, valign: "top", isTextBox: true });
  s.addText(lines([["Reading: ", "49.9 %"], ["Band: ", "50–60 %, target 55 %"], ["Short by: ", "5.1 points"], ["Dose: ", "5.1 × 3.18 = 16.2 mL"],
    ["Valve open: ", "0.90 s × 18 mL/s = 16.2 mL ✓"]], 14),
    { x: 10.15, y: 2.25, w: 2.45, h: 3.1, fontFace: BF, margin: 0, valign: "top", paraSpaceAfter: 8, isTextBox: true });
  s.addText("Logged in irrigation_log.csv, with no one touching it", { x: 10.15, y: 5.55, w: 2.45, h: 0.9, fontFace: BF, fontSize: 12, italic: true, color: MUTED, margin: 0, valign: "top", isTextBox: true });
}

// 5. Moisture now vs bands --------------------------------------------------------
{
  const s = content("Moisture now: the controller is holding off", "D1");
  const pots = [["P-01", "Low", 65.0], ["P-02", "Low", 80.7], ["P-03", "Low", 67.1], ["P-04", "Optimal", 91.0], ["P-05", "Optimal", 57.1],
    ["P-06", "Optimal", 68.7], ["P-07", "High", 97.0], ["P-08", "High", 80.9], ["P-09", "High", 90.7]];
  const band = { Low: [30, 40], Optimal: [50, 60], High: [70, 80] };
  const X0 = 1.6, TW = 6.6, Y0 = 1.55, RH = 0.5;
  const xs = (v) => X0 + (v / 100) * TW;
  [0, 25, 50, 75, 100].forEach((v) => {
    s.addShape(pres.shapes.LINE, { x: xs(v), y: Y0 - 0.05, w: 0, h: 9 * RH + 0.25, line: { color: LINE, width: 0.75 } });
    s.addText(v + " %", { x: xs(v) - 0.4, y: Y0 + 9 * RH + 0.25, w: 0.8, h: 0.3, fontFace: BF, fontSize: 11, color: MUTED, align: "center", margin: 0, isTextBox: true });
  });
  pots.forEach(([p, g, v], i) => {
    const y = Y0 + i * RH + (i >= 3 ? 0.06 : 0) + (i >= 6 ? 0.06 : 0);
    s.addText(p, { x: 0.6, y, w: 0.9, h: RH - 0.08, fontFace: BF, fontSize: 14, bold: true, color: INK, valign: "middle", margin: 0, isTextBox: true });
    s.addShape(pres.shapes.RECTANGLE, { x: X0, y: y + 0.12, w: TW, h: RH - 0.32, fill: { color: "F1F3F1" }, line: { color: "F1F3F1" } });
    const [a, b] = band[g];
    s.addShape(pres.shapes.RECTANGLE, { x: xs(a), y: y + 0.05, w: xs(b) - xs(a), h: RH - 0.18, fill: { color: GRP[g], transparency: 70 }, line: { color: GRP[g], width: 1 } });
    s.addShape(pres.shapes.OVAL, { x: xs(v) - 0.11, y: y + 0.03, w: 0.22, h: 0.22 + 0.0, fill: { color: GRP[g] }, line: { color: WHITE, width: 1.5 } });
    s.addText(v.toFixed(1) + " %", { x: TW + X0 + 0.15, y, w: 0.95, h: RH - 0.08, fontFace: BF, fontSize: 14, color: INK, valign: "middle", margin: 0, isTextBox: true });
  });
  s.addText("Box = the pot's band from D8 · dot = reading at 15:10 today", { x: 0.6, y: 6.45, w: 8.6, h: 0.35, fontFace: BF, fontSize: 12, color: MUTED, margin: 0, isTextBox: true });

  card(s, 9.55, 1.45, 3.2, 5.2);
  s.addText(bullets([
    ["8 of 9 pots are above their band, ", "so the ESP32 correctly does not water. Each check is logged as ABOVE_BAND."],
    ["P-05 is inside its band ", "(57 %), so it doesn't need water either."],
    ["The pots dry down over the next days, ", "then automatic watering starts."],
  ], 14), { x: 9.75, y: 1.6, w: 2.85, h: 4.9, fontFace: BF, margin: 0, valign: "top", isTextBox: true });
}

// 6. Masking / GPR calculation ----------------------------------------------
{
  const s = content("How GPR is measured: masking the green", "D2 · D3");
  s.addImage({ path: img("d08raw.jpg"), x: 0.6, y: 1.4, w: 3.75, h: 3.75, altText: "D8 noon photo" });
  s.addImage({ path: img("d08.jpg"), x: 4.5, y: 1.4, w: 3.75, h: 3.75, altText: "D8 noon photo with the green mask and pot areas" });
  s.addText("D8 noon photo", { x: 0.6, y: 5.2, w: 3.75, h: 0.3, fontFace: BF, fontSize: 12, color: MUTED, margin: 0, isTextBox: true });
  s.addText("Green mask and pot areas", { x: 4.5, y: 5.2, w: 3.75, h: 0.3, fontFace: BF, fontSize: 12, color: MUTED, margin: 0, isTextBox: true });
  const steps = [["1  Fixed camera", "Locked gain and white balance; same brightness (V 73) at 12:00"],
    ["2  Keep green pixels", "Hue 38–85 (OpenCV units, about 76°–170°), saturation ≥ 100, brightness ≥ 55"],
    ["3  Clean the mask", "3 × 3 opening removes specks"],
    ["4  Count per pot", "GPR = green pixels ÷ pot-area pixels × 100"]];
  steps.forEach(([a, b], i) => {
    const y = 1.4 + i * 0.98;
    s.addText(a, { x: 8.6, y, w: 4.15, h: 0.35, fontFace: BF, fontSize: 15, bold: true, color: GREEN, margin: 0, isTextBox: true });
    s.addText(b, { x: 8.6, y: y + 0.35, w: 4.15, h: 0.6, fontFace: BF, fontSize: 13, color: INK, margin: 0, valign: "top", isTextBox: true });
  });
  card(s, 0.6, 5.65, 12.15, 1.05, "F4F6F4");
  s.addText([
    { text: "Worked example, P-07 on D8:  ", options: { bold: true, color: DARK } },
    { text: "230 green pixels ÷ 96,209 pixels in its area × 100 = ", options: { color: INK } },
    { text: "0.24 %", options: { bold: true, color: GREEN } },
  ], { x: 0.85, y: 5.65, w: 11.7, h: 1.05, fontFace: BF, fontSize: 17, valign: "middle", margin: 0, isTextBox: true });
}

// 7. Glare --------------------------------------------------------------------
{
  const s = content("Glare: detected, flagged and fixed", "D2 · D3");
  s.addImage({ path: img("before.jpg"), x: 0.6, y: 1.4, w: 3.9, h: 3.9, altText: "Masked photo at 11:35 before the cloths, with glare" });
  s.addImage({ path: img("after.jpg"), x: 4.7, y: 1.4, w: 3.9, h: 3.9, altText: "Masked photo at 11:50 with cloths, glare gone" });
  s.addText("Before: D8 11:35", { x: 0.6, y: 5.35, w: 3.9, h: 0.35, fontFace: BF, fontSize: 13, bold: true, color: GRP.Low, margin: 0, isTextBox: true });
  s.addText("After cloths: D8 11:50", { x: 4.7, y: 5.35, w: 3.9, h: 0.35, fontFace: BF, fontSize: 13, bold: true, color: GREEN, margin: 0, isTextBox: true });
  s.addText("Small cloths over P-01, P-04 and P-07, where the noon sun lands. Full shade cloth over all 9 pots from D9.",
    { x: 0.6, y: 5.75, w: 8.0, h: 0.8, fontFace: BF, fontSize: 14, color: INK, margin: 0, valign: "top", isTextBox: true });
  s.addText("Light check, every noon photo", { x: 9.0, y: 1.4, w: 3.75, h: 0.4, fontFace: BF, fontSize: 16, bold: true, color: DARK, margin: 0, isTextBox: true });
  const lv = [["44", "ok", GREEN], ["4", "MILD: 1.4× brighter than the other pots", AMBER], ["4", "GLARE: also ≥ 5 % burnt-out pixels", GRP.Low], ["2", "DARK: ≤ 0.6× (deep shade)", MUTED]];
  lv.forEach(([a, b, c], i) => {
    const y = 1.95 + i * 0.85;
    s.addText(a, { x: 9.0, y, w: 0.9, h: 0.7, fontFace: HF, fontSize: 30, bold: true, color: c, valign: "middle", margin: 0, isTextBox: true });
    s.addText(b, { x: 9.95, y, w: 2.8, h: 0.7, fontFace: BF, fontSize: 13, color: INK, valign: "middle", margin: 0, isTextBox: true });
  });
  s.addText("of 54 pot photos, D1–D8 (glare_log.csv). Flagged days are kept, not deleted: the model is run with and without them.",
    { x: 9.0, y: 5.45, w: 3.75, h: 1.2, fontFace: BF, fontSize: 13, color: MUTED, margin: 0, valign: "top", isTextBox: true });
}

// 8. GPR time series -----------------------------------------------------------
{
  const s = content("Green pixel ratio per pot, D1–D8", "D3");
  s.addImage({ path: img("gpr.png"), x: 0.6, y: 1.35, w: 12.13, h: 4.2, altText: "Line charts of GPR by day for each pot in three panels by moisture group" });
  s.addText(bullets([
    ["D2 and D3 are blank: ", "no power at noon. Missed days are never filled in."],
    ["P-07 on D6–D7 reads 0 because of glare, ", "P-03 on D7 is a green object outside the pot. Both flagged."],
    ["Before the D8 photo: ", "transplants into P-01, P-03, P-06; cloths over P-01, P-04, P-07."],
  ], 14), { x: 0.6, y: 5.65, w: 12.13, h: 1.25, fontFace: BF, margin: 0, valign: "top", isTextBox: true });
}

// 9. Vision reliability ------------------------------------------------------------
{
  const s = content("Vision reliability: ROI and GPR", "D7");
  stat(s, 0.6, 1.3, 2.9, "0.64", "Overlap (IoU) with hand labels. Two people: 0.79");
  stat(s, 3.7, 1.3, 2.9, "0.28 pp", "Average GPR error. Two people: 0.19 pp");
  stat(s, 6.8, 1.3, 2.9, "+0.04 pp", "Bias: no tendency to over- or under-count");
  stat(s, 9.9, 1.3, 2.85, "23 / 24", "Empty-pot photos that read 0.00 %");
  s.addImage({ path: img("errmap.jpg"), x: 0.6, y: 3.3, w: 6.6, h: 3.3, altText: "Error map: where the program and the hand label disagree" });
  s.addText("Green = agree · red = missed by the program · blue = extra (run 1, D13)", { x: 0.6, y: 6.62, w: 6.6, h: 0.3, fontFace: BF, fontSize: 11, color: MUTED, margin: 0, isTextBox: true });
  card(s, 7.55, 3.3, 5.2, 3.3);
  s.addText(bullets([
    ["Pot circles (ROI): ", "camera drifted about 16 px by D6, re-centred and logged; 1 px on D7. Old files kept as backups."],
    ["Same light every day: ", "brightness 70.6–74.9 against the target 73; capture light never needed."],
    ["Not yet as close as two people ", "(0.64 vs 0.79) on tiny seedlings. Re-checked on run 2 photos around D20 and D26."],
  ], 14), { x: 7.75, y: 3.45, w: 4.85, h: 3.05, fontFace: BF, margin: 0, valign: "top", isTextBox: true });
}

// 10. Power and uptime ------------------------------------------------------------
{
  const s = content("Power and uptime: honest numbers", "D7");
  const days = ["Oct 29", "Oct 30", "Oct 31", "Nov 1", "Nov 2", "Nov 3", "Nov 4", "Nov 5"];
  const vals = [5, 2, 10, 5, 2, 19, 1, 6];
  s.addChart(pres.charts.BAR, [{ name: "Pi restarts", labels: days, values: vals }], {
    x: 0.6, y: 1.35, w: 7.2, h: 4.4, barDir: "col", chartColors: [GREEN], showValue: true, dataLabelPosition: "outEnd",
    dataLabelColor: INK, dataLabelFontSize: 12, dataLabelFontFace: BF,
    showTitle: true, title: "Pi restarts per day (power_log.csv)", titleFontFace: BF, titleFontSize: 14, titleColor: DARK,
    catAxisLabelColor: MUTED, valAxisLabelColor: MUTED, catAxisLabelFontFace: BF, valAxisLabelFontFace: BF,
    catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, valGridLine: { color: "E3E7E3", size: 0.75 }, catGridLine: { style: "none" },
    showLegend: false, barGapWidthPct: 60, valAxisMaxVal: 22,
  });
  s.addText("50 restarts since sowing; 39 were the Pi only, while the ESP32 kept watering.", { x: 0.6, y: 5.85, w: 7.2, h: 0.8,
    fontFace: BF, fontSize: 14, color: INK, margin: 0, valign: "top", isTextBox: true });
  stat(s, 8.3, 1.3, 2.1, "6 / 8", "Noon photos taken (D2, D3 lost to power)");
  stat(s, 10.6, 1.3, 2.15, "0", "Low-voltage flags since logging began (Nov 4)");
  card(s, 8.3, 3.4, 4.45, 3.25);
  s.addText("Fixes so far", { x: 8.5, y: 3.5, w: 4.1, h: 0.4, fontFace: BF, fontSize: 16, bold: true, color: DARK, margin: 0, isTextBox: true });
  s.addText(bullets([
    ["Nov 4: ", "auto-restart watchdog and a voltage log every 5 min"],
    ["Nov 5: ", "12 V supply upgraded from 1 A to 2.5 A"],
    ["Since then: ", "5 short Pi restarts, each back in 1–4 min, all while Wi-Fi was searching. Next fix: the Wi-Fi reconnect routine."],
  ], 14), { x: 8.5, y: 3.95, w: 4.1, h: 2.6, fontFace: BF, margin: 0, valign: "top", isTextBox: true });
}

// 11. Deviation log -----------------------------------------------------------
{
  const s = content("Everything done by hand is logged");
  const ev = [
    ["D1", "Pi off at noon; D1 photo taken by hand at 13:14. Pot circles fitted after the camera moved."],
    ["D2–D3", "Noon photos missed (power). Left blank."],
    ["D1–D7", "Hand spraying during germination, logged with times and pots."],
    ["D6", "Camera drift about 16 px; pot circles re-centred from D7."],
    ["D7", "P-03 green object outside the pot; Pi froze in the afternoon."],
    ["D8 11:00", "Spare seedlings moved into empty P-01, P-03, P-06."],
    ["D8 11:10", "12 V power supply changed, 1 A to 2.5 A."],
    ["D8 11:40", "Small cloths over P-01, P-04, P-07 against glare."],
    ["D8 11:44", "Germination mode off, treatment bands on."],
    ["D8 15:15", "P-09 got about 90 mL by mistake during a valve test (5 s)."],
  ];
  ev.forEach(([d, t], i) => {
    const col = i < 5 ? 0 : 1, r = i % 5;
    const x = 0.6 + col * 6.2, y = 1.45 + r * 1.0;
    card(s, x, y, 5.95, 0.85, col === 1 ? TINT : "F4F6F4");
    s.addText(d, { x: x + 0.2, y, w: 1.25, h: 0.85, fontFace: BF, fontSize: 15, bold: true, color: GREEN, valign: "middle", margin: 0, isTextBox: true });
    s.addText(t, { x: x + 1.5, y, w: 4.3, h: 0.85, fontFace: BF, fontSize: 14, color: INK, valign: "middle", margin: 0, isTextBox: true });
  });
  s.addText("All in field_log.csv, also attached to each pot's GPR file (DATA/thesis/gpr_per_pot/)", { x: 0.6, y: 6.5, w: 12.1, h: 0.35, fontFace: BF, fontSize: 12, italic: true, color: MUTED, margin: 0, isTextBox: true });
}

// 12. Limitations and next steps ------------------------------------------------
{
  const s = pres.addSlide(); n++;
  s.background = { color: DARK };
  s.addText("Limitations and next steps", { x: 0.6, y: 0.35, w: 12, h: 0.8, fontFace: HF, fontSize: 32, bold: true, color: WHITE, margin: 0, valign: "middle", isTextBox: true });
  const lim = [["Groups are in rows", "light can differ by row; logged hourly per pot"],
    ["3 plants per group", "a proof of concept, tested with leave-one-plant-out"],
    ["Moisture is relative", "oven-dry to saturated, not true VWC"],
    ["3 transplanted pots", "moved on D8, before treatments; logged"]];
  s.addText("Limitations we report", { x: 0.6, y: 1.45, w: 5.8, h: 0.45, fontFace: BF, fontSize: 18, bold: true, color: MOSS, margin: 0, isTextBox: true });
  lim.forEach(([a, b], i) => {
    const y = 2.05 + i * 1.12;
    s.addText(a, { x: 0.6, y, w: 5.8, h: 0.4, fontFace: BF, fontSize: 16, bold: true, color: WHITE, margin: 0, isTextBox: true });
    s.addText(b, { x: 0.6, y: y + 0.4, w: 5.8, h: 0.5, fontFace: BF, fontSize: 14, color: "D6E6D2", margin: 0, isTextBox: true });
  });
  const nx = [["Nov 6 (D9)", "Full shade cloth over all 9 pots"], ["Next week", "Day 0 pH of all 9 pots (PH-4502C sensor)"],
    ["After checking", "Fix the Wi-Fi reconnect freeze"], ["D20, D26", "Re-check GPR against hand labels"],
    ["Nov 27 (D30)", "Harvest and weigh; 6-term model, tested with LOOCV (R², MAE)"]];
  s.addText("Next steps", { x: 7.0, y: 1.45, w: 5.75, h: 0.45, fontFace: BF, fontSize: 18, bold: true, color: MOSS, margin: 0, isTextBox: true });
  nx.forEach(([a, b], i) => {
    const y = 2.05 + i * 0.9;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.0, y, w: 5.75, h: 0.75, rectRadius: 0.1, fill: { color: "2C5239" }, line: { color: "2C5239" } });
    s.addText(a, { x: 7.2, y, w: 1.75, h: 0.75, fontFace: BF, fontSize: 14, bold: true, color: MOSS, valign: "middle", margin: 0, isTextBox: true });
    s.addText(b, { x: 9.0, y, w: 3.6, h: 0.75, fontFace: BF, fontSize: 14, color: WHITE, valign: "middle", margin: 0, isTextBox: true });
  });
  s.addText("Manuscript fixes in progress: LED removed, 30-day harvest, Camera Module 3, 9 sensors and valves in the BOM, hue in OpenCV units.",
    { x: 0.6, y: 6.6, w: 12.1, h: 0.5, fontFace: BF, fontSize: 12, color: "B8CCB4", margin: 0, isTextBox: true });
}

pres.writeFile({ fileName: path.join(D, "Pechay_Run2_D8_checking.pptx") }).then((f) => console.log("wrote", f));
