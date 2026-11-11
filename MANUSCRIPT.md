# AgriSentry: Manuscript Tracking & Revision Guide

> **Quick Reference for Agents & Proponents:**  
> This file tracks the exact state, empirical parameters, verified corrections, and LaTeX specifications for the undergraduate thesis manuscript:  
> **"Computer Vision-Based Growth Monitoring and Yield Prediction for Pechay Under Differential Soil Moisture Treatments in a Greenhouse"**  
> *University of San Carlos — Department of Computer Engineering (CPE 3207L)*  
> *Proponents:* Rey Emmanuel Adag, Kent Vincent Godinez, Cedric Vince Tan  
> *Advisers:* Engr. Alvin Joseph Macapagal (Main), Engr. Linda Saavedra (Assistant)  
> *Panel:* Dr. Luis Gerardo S. Cañete, Jr. (Chair), Engr. Andre Kimberly Trish D'Silva, Engr. Kenneth Carl Labarosa

---

## 1. Executive Summary & Ground Truth Status

* **Cultivation Run:** Run 2 (sown October 29, 2026 = Day 1).
* **Cycle Duration:** **30 days** (D1 = Oct 29, 2026; Harvest on **Day 30 = November 27, 2026**).
* **Current Stage:** Active vegetative growth (D14 as of Nov 11, 2026).
* **Treatment Timeline:** Germination mode (all pots held at 50–60%) D1 to D8 (Nov 5). Treatment bands activated at D8 11:44 AM.
* **Integrity Rule:** No synthetic or back-filled data. Power outage across D2 and D3 is transparently reported as missed captures.

---

## 2. Critical Discrepancies: Proposal Text vs. Real Bench Setup

When revising Chapters 1–3 and drafting Chapters 4–5, update the following proposal draft assumptions with verified bench data:

| Aspect | Proposal Draft Text (`Group-B_revisions.pdf`) | Actual Implementation (To Be Updated) | Verification Source |
| :--- | :--- | :--- | :--- |
| **Cycle Length** | 35 days (315 rows) | **30 days (up to 270 rows)** | Approved by Sir AJ (Oct 29); `CYCLE_DAYS = 30` in `capture_gpr.py` |
| **Pot Dimensions** | Upper diameter 200 mm, depth 200 mm | **Top diameter 11.0 cm, base 8.5 cm, depth 8.0 cm** (truncated cone) | Bench measurements (Nov 9, 2026) |
| **Pot Soil Volume** | Approximately 3.0 L | **$601\text{ cm}^3$ ($0.60\text{ L}$)** | Geometric calculation: $V = \frac{\pi h}{3}(R^2 + Rr + r^2)$ |
| **Pot Substrate Weight** | Not quantified in proposal | **388 g dry / 662 g saturated** (holds $274\text{ mL}$ water) | Scale measurements (5 kg / 1 g resolution) |
| **Substrate Recipe** | Generic DA soil mix (loam, compost, carbonized rice husk) | **8:4:3 volumetric ratio** (Garden soil : Carbonized Rice Hull : Vermicast) | Proponent recipe (53.3% loam, 26.7% CRH, 20.0% vermi) |
| **Moisture Metric** | Assumed true VWC | **Relative moisture scale ($0\text{--}100\%$) mapped to True VWC** ($100\%\text{ rel} \approx 45.6\%\text{ VWC}$, factor $\times 0.456$) | `calibration_log.md` Section 4c |
| **Camera Module** | Camera Module V2 ($48.8^\circ$ VFOV) at 1100 mm | **Camera Module 3 (Sony IMX708)** mounted at 136 cm above soil plane | Hardware deployment; fixed focus, locked WB, auto-exposure to $V = 73$ |
| **Opening Kernel** | $9 \times 9$ or $5 \times 5$ morphological opening | **$3 \times 3$ opening kernel (`MORPH_K = 3`)** | $9 \times 9$ erased cotyledons $< 6.7\text{ mm}$; $3 \times 3$ keeps $98.4\%$ true pixels |
| **GPR Spatial Metric** | Pot circle only ($r = 77\text{ px}$) | **Pot-area Cell GPR (`cell_gpr`)** via Voronoi partitioning (up to 175 px radius) | Solves leaning seedlings dropping out of rigid pot rims |
| **Image Retention** | Raw images purged daily | **Lossless raw noon PNGs retained in `frames/`** | Preserved from D12 onward for phase-correlation alignment & validation |
| **Regression Model** | 8-term polynomial | **Parsimonious 6-term polynomial** (removed $D^2$ and $D \times \text{GPR}$ due to collinearity) | Section III.F, `analyze_yield.py` |

---

## 3. Updated Table I: Verifiable Deliverables (Drop-in LaTeX)

```latex
\vspace{0.5\baselineskip}
\noindent \textbf{b) Verifiable Project Deliverables:}
\begin{table}[H]
\caption{Verifiable Deliverables Mapped to Specific Research Objectives}
\label{tab:deliverables}
\centering
\begin{tabularx}{\linewidth}{p{0.45\linewidth} p{0.5\linewidth}}
\toprule
\textbf{Specific Objective} & \textbf{Verifiable Deliverables} \\
\midrule
1. Deploy 1:1 solenoid baseline irrigation for 3 differential soil moisture treatment groups (Low 30--40\%, Optimal 50--60\%, High 70--80\%). & Two-point sensor calibration log (oven-dried vs. saturated ADC baseline with VWC conversion factor); 30-day automated irrigation log (CSV) with timestamps, Pot ID, soil moisture (\%), dose volumes (mL), and pulse durations. \\
\midrule
2. Establish uniform growing environment and controlled agronomic conditions. & Standardized 8:4:3 potting substrate specification (garden soil:carbonized rice hull:vermicast); Baseline soil pH spot-check table for 9 pots; Pre-calibration vision report (HSV bounds, $3\times 3$ morphological opening, locked exposure); ROI mask configuration file (\texttt{pot\_rois.json}) with pot-area cell boundaries. \\
\midrule
3. Capture daily canopy images and compute Green Pixel Ratio (GPR) for 9 plants over a 30-day grow-out cycle. & Nine 30-day GPR time-series CSV files (Date, Timestamp, Pot ID, Soil Moisture, Raw GPR, Cell GPR, Smoothed GPR, Anomaly Flag); Daily system capture and exposure log; Multi-group GPR canopy trajectory plots. \\
\midrule
4. Collect ground-truth fresh-weight biomass at harvest. & 9-pot harvest fresh-weight table (Pot ID, Treatment Group, Harvest Date, Fresh Weight in grams); Digital scale calibration check-sheet. \\
\midrule
5. Formulate multivariate polynomial regression model. & Full 30-day training dataset CSV (up to 270 rows); Parsimonious 6-term polynomial regression equation with explicit $\beta_0$--$\beta_5$ coefficients; Feature correlation matrix and multicollinearity evaluation. \\
\midrule
6. Evaluate model predictive performance via Leave-One-Plant-Out Cross-Validation (LOOCV). & LOOCV $R^2$ score; Mean Absolute Error (MAE in grams, reported per-plant and per-row); Predicted vs. actual harvest weight table; Residual plots per soil moisture treatment group. \\
\midrule
7. Implement software-level failure detection, anomaly tracking, and system recovery. & 30-day error, power, and glare log files (\texttt{error\_log.csv}, \texttt{power\_log.csv}, \texttt{glare\_log.csv}); System reliability summary report (capture completeness, outage recovery, fault quarantines, and GPR segmentation accuracy benchmarked against manual hand-labels). \\
\bottomrule
\end{tabularx}
\end{table}
\vspace{0.5\baselineskip}
```

---

## 4. Mathematical Model & Statistical Equations

### 4.1 The 6-Term OLS Polynomial Model
$$\hat{Y} = \beta_0 + \beta_1 D + \beta_2 \text{GPR} + \beta_3 \text{SM} + \beta_4 \text{GPR}^2 + \beta_5 (\text{GPR} \times \text{SM}) + \varepsilon$$

* $\hat{Y}$: Predicted final harvest fresh weight (grams).
* $D$: Chronological day index in growth cycle ($1 \le D \le 30$).
* $\text{GPR}$: Green Pixel Ratio (`cell_gpr` percentage).
* $\text{SM}$: Relative soil moisture percentage (or converted VWC).
* $\beta_0 \dots \beta_5$: Ordinary Least Squares learned coefficients.
* $\varepsilon$: Residual error term.

### 4.2 Leave-One-Plant-Out Cross-Validation (LOOCV)
Because observations within a single plant's 30-day time-series are temporally autocorrelated, models must never be evaluated using a random row-wise split. 
* Training is performed on 8 plants ($n = 240$ rows), evaluating the held-out 9th plant ($n = 30$ rows), iterated 9 times.
* Performance metrics:
  $$R^2 = 1 - \frac{\sum (Y_{\text{actual}} - \hat{Y})^2}{\sum (Y_{\text{actual}} - \bar{Y})^2}$$
  $$\text{MAE}_{\text{plant}} = \frac{1}{9} \sum_{i=1}^9 \left| Y_{\text{actual},i} - \bar{\hat{Y}}_i \right|$$

---

## 5. Soil Moisture Calibration & VWC Physics

* **Oven-Dried Point ($0\%$ relative):** $2483\text{ ADC}$ (dried at 150 °C for 6 h).
* **Saturated Soil Point ($100\%$ relative):** $1120\text{ ADC}$ (saturated DA mix).
* **Span:** 1363 ADC counts.
* **Air Offsets:** P-03 shifted by $-103$; P-05 shifted by $-75$ so all probes read identically in air ($\sim 5.9\%$).
* **Volumetric Water Content (VWC) Mapping:**
  $$\text{VWC} \approx \text{Relative } \% \times \frac{274\text{ mL water}}{601\text{ mL soil volume}} \approx \text{Relative } \% \times 0.456$$

| Treatment Group | Relative Moisture Band | Equivalent True VWC |
| :--- | :--- | :--- |
| **Group A (Low)** | $30\%\text{ to } 40\%$ | $13.7\%\text{ to } 18.2\%$ |
| **Group B (Optimal)** | $50\%\text{ to } 60\%$ | $22.8\%\text{ to } 27.4\%$ |
| **Group C (High)** | $70\%\text{ to } 80\%$ | $31.9\%\text{ to } 36.5\%$ |
| **Saturated Soil** | $100\%$ | $45.6\%$ |
| **Oven-Dry Soil** | $0\%$ | $0.0\%$ |

---

## 6. Key Literature References for Revisions & Defense

1. **Pak Choi Growth Curves:**  
   * *Ding et al. (2022)*, *HortScience* 57(5): 643–651. Proves pak choi leaf expansion in greenhouses follows 3-parameter logistic curves ($R^2 > 0.98$).
   * *Cho et al. (2015)*, *Hort. Environ. Biotechnol.* 56(3): 310–315. Demonstrates expolinear growth for pak choi dry/fresh weight ($R^2 = 0.982$).
2. **Early Image Time-Series Forward Projection:**  
   * *Hosoda et al. (2024)*, *IEEE Access* 12: 97226–97234. Uses 10 days of early plant images to predict fresh weight 10 days ahead ($R^2 = 0.885$).
   * *Kim & van Iersel (2022)*, *Remote Sensing* 14(2): 316. Validates early projected canopy area as a predictor of final biomass ($R^2 = 0.74$).
3. **Vegetation Fraction Under Moisture Treatments:**  
   * *Lee & Park (2024)*, *Remote Sensing* 16(18): 3455. Uses image vegetation fraction to predict *Brassica rapa* fresh weight under varying irrigation regimes.
4. **Institutional Lineage (USC):**  
   * *Aala et al. (2022)* — Initial IoT precision farming prototype at USC.
   * *Zamora et al. (2025)* — Solenoid baseline automated irrigation for pechay (+92.1% yield vs. manual watering).

---

## 7. Data & File Manifest

* **Manuscript Source:** `/Users/moapilaw/Desktop/THESIS/Group-B_revisions.pdf`
* **Live Datasets:**
  * Master GPR dataset: `DATA/thesis/growth_dataset.csv`
  * Soil moisture (30-min): `DATA/agrisentry_data/sm_log.csv`
  * Irrigation events: `DATA/agrisentry_data/irrigation_log.csv`
  * System field events: `DATA/thesis/field_log.csv`
  * Exposure & Glare logs: `DATA/thesis/exposure_log.csv`, `DATA/thesis/glare_log.csv`
  * Reliability & Power outages: `DATA/agrisentry_data/power_log.csv`, `DATA/agrisentry_data/error_log.csv`
* **Core Code & Firmware:**
  * Vision capture daemon: `Dual_Archi/capture_gpr.py`
  * Pi-ESP32 link daemon: `Dual_Archi/pi_link.py`
  * ESP32 firmware: `Dual_Archi/Dual_Archi_Firmware/src/main.cpp`
  * Yield analysis & LOOCV: `Dual_Archi/analyze_yield.py`
  * Harvest recording tool: `Dual_Archi/record_harvest.py`
  * Reliability reporter: `Dual_Archi/reliability_report.py`

---

## 8. Current Chapter Status (November 12, 2026 Pass)

| Chapter / File | Status | Summary of Content / Completed Actions |
| :--- | :--- | :--- |
| **`thesis.tex`** | **Active / Clean** | Main USC thesis root file. Configured for both XeTeX/Tectonic and pdfLaTeX. |
| **`Chapter1/`** | **Complete** | Converted to past/present tense. Standardized 8:4:3 substrate, truncated cone pots ($601\text{ cm}^3$), 30-day cycle (up to 270 rows), Voronoi `cell_gpr`, and 6-term OLS model. Table 1.1 updated. |
| **`Chapter2/`** | **Complete** | Converted to past/present tense. Added 5 literature citations (Ding 2022, Cho 2015, Hosoda 2024, Kim 2022, Lee 2024). Corrected greenhouse lighting description to natural daylight with brightness normalization ($V=73$). |
| **`Chapter3/`** | **Complete** | Converted to past/present tense. Fully reconciled bench parameters: pot volume $601\text{ cm}^3$, substrate weight 388 g dry / 662 g saturated, Camera Module 3 at 136 cm elevation, two-point calibration mapped to True VWC ($\times 0.456$), always-on power with UPS, Voronoi cell masks ($r \le 175\text{ px}$), $3 \times 3$ opening kernel, 6-term polynomial model, and LOOCV. Added CAD housings, timber greenhouse, and GPR hand-label validation methodology. |
| **`Chapter4/`** | **In Progress (Run 2)** | Populated with empirical data up to Day 12 (90 rows written, D2–D3 outage reported transparently without interpolation, treatment adherence analyzed). Harvest analysis sections are scaffolded with `\pending{}` blocks ready for Day 30 harvest weights (`harvest_weights.csv`). |
| **`Chapter5/`** | **Skeleton** | Scaffolded structure ready for conclusions and recommendations upon completion of Chapter 4. |
| **`References/`** | **Complete** | Clean IEEEtran-compliant BibTeX database containing all 26 citations (21 original + 5 new literature references). |
| **`Appendices/`** | **Updated** | Appendix 4 (BOM updated to 9 sensors, 9 valves, IMX708, BMP388, cooling fans; currency symbols fixed). Appendix 6 (WBS updated to 30-day grow-out). Appendix 7 (Vision pseudocode updated to Voronoi cells, $V=73$ exposure, $3 \times 3$ opening, PNG archival). Appendix 8 (CSV log schema updated with `Cell GPR`). |
| **`REVISION_LETTER.md`** | **Ready** | Formal 9-item revision letter to the panel (Dr. Cañete, Engr. D’Silva, Engr. Labarosa) detailing all empirical adjustments with rationale and citations. |

---

## 9. Compilation & Live Preview Guide (For Proponents & AI Agents)

The thesis manuscript directory is located at `2026-11-11-GroupB-Manuscript-Draft1/`.

### Quick Terminal Build:
To compile the complete 78-page PDF document at any time:
```bash
cd 2026-11-11-GroupB-Manuscript-Draft1
./compile.sh
```
*(Runs via `tectonic thesis.tex`, resolving cross-references, BibTeX citations, table of contents, and nomenclature in ~5 seconds).*

### Live Auto-Recompile on Save:
A lightweight background file watcher is available:
```bash
python3 2026-11-11-GroupB-Manuscript-Draft1/auto_watch.py
```
Whenever any `.tex` or `.bib` file is edited and saved, `auto_watch.py` detects the change and automatically recompiles `thesis.pdf`.

### Live Viewing in Antigravity IDE / VS Code:
1. Open `thesis.pdf` in a tab side-by-side with your code (`Right-click -> Open to the Side`).
2. Alternatively, view it in macOS native Preview:
   ```bash
   open 2026-11-11-GroupB-Manuscript-Draft1/thesis.pdf
   ```
   *(macOS Preview automatically live-refreshes every time `thesis.pdf` recompiles).*


### 8.1 Live Compilation & Word Count Metrics

| Metric | Current Value |
| :--- | :--- |
| **Last Compilation** | `2026-11-12 01:11:43` (Passing, 95 pages in 4.6s) |
| **Chapter 1 Words** | 2393 words |
| **Chapter 2 Words** | 2477 words |
| **Chapter 3 Words** | 2448 words |
| **Chapter 4 Words** | 2765 words (Run 2 in progress) |
| **Total Chapters Word Count** | **10083 words** (95 pages) |

