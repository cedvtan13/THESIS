# Migration notes, Group B

Read this once before anyone edits a chapter.

## What was done to this project

Your proposal was migrated into the USC long-format template. Nothing under
`Classes/`, `sty/` or `Declaration/` was touched, as Maam Antoi asked.
`thesis-info.tex` is exactly as you had it.

| Change | Where |
|---|---|
| Headings shifted one level up: `\section` to `\chapter`, `\subsection` to `\section`, `\subsubsection` to `\subsection` | Chapters 1 to 3 |
| 21 references converted from `\bibitem` to BibTeX. Citation keys unchanged, so every `\cite{...}` still works. The template's 42 demo entries were deleted | `References/references.bib` |
| Figures moved out of the pooled `uploads/` and `prism-uploads/` folders into the chapter that uses them | `Chapter2/Figs/`, `Chapter3/Figs/`, `Appendix*/Figs/` |
| `\columnwidth` changed to `\linewidth` | Chapters 2 and 3, appendices |
| IEEE two-column spacing crutches removed: the `\hspace*{1.5em}` paragraph indents and the `\vspace{0.5\baselineskip}` gaps. The book class indents and spaces paragraphs on its own, so leaving them in produced double indents and uneven gaps | Chapters 1 to 3 |
| The ten appendices in `main.tex` split into one folder and file each | `Appendix1` to `Appendix10` |
| Four packages enabled in the preamble: `float` and `tabularx` were shipped commented out and your tables need both; `pdfpages`, `placeins` and `algorithmic` were in your proposal's `main.tex` | `Preamble/preamble.tex` |
| Nomenclature filled with 29 entries: 5 Roman symbols, 2 Greek, 22 acronyms | end of `Chapter1/chapter1.tex` |
| Chapters 4 and 5, the abstract and the acknowledgment created as commented skeletons | respective folders |

**No wording in Chapters 1 to 3 was changed.** Every sentence is still the one
you wrote. The tense pass and the content corrections are listed below and are
yours to make.

## Verified

The project compiles. 78 pages with the bibliography, A4, two-sided. All 21
references resolve, no undefined citations, no undefined cross-references, no
missing figures. The table of contents, list of figures, list of tables and
nomenclature all generate automatically.

One caveat: `IEEEtran.bst` is not installed in the machine this was checked on,
so the bibliography was verified with a stand-in style. Prism has `IEEEtran`.
`\bibliographystyle{IEEEtran}` is left in `thesis.tex` as Maam Antoi instructed.
Run a compile in Prism before you change anything, to confirm it builds there.

## Status Update (November 12, 2026 Pass - Completed)

The mechanical and content revisions required for Chapters 1 to 3, references, and appendices have been fully executed and verified:

1. **Tense Pass & Scope Harmonization (Chapters 1, 2, 3):**
   - Past tense for implemented hardware/experimentation, present tense for established facts.
   - Updated grow-out cycle from 35 days (315 rows) to **30 days (up to 270 rows)**.
   - Ground truth substrate recipe: **8:4:3 volumetric ratio** (garden soil : carbonized rice hull : vermicast).
   - Container dimensions: Truncated cone polyethylene pots (**11.0 cm top, 8.5 cm base, 8.0 cm depth**; volume $601\text{ cm}^3$ / $0.60\text{ L}$; 388 g dry / 662 g saturated).
   - Sensor calibration: Two-point calibration (2483 ADC dry to 1120 ADC saturated, 1363 ADC span) mapped to True VWC via factor $\times 0.456$.
   - Vision & Camera: Camera Module 3 (Sony IMX708) mounted at 136 cm elevation, fixed focus, locked WB, auto-exposure to $V = 73$; Voronoi pot-area `cell_gpr` ($r \le 175\text{ px}$); $3 \times 3$ morphological opening (`MORPH_K = 3`); lossless raw noon PNG archival from D12.
   - Modeling: Parsimonious 6-term polynomial regression model with LOOCV.
   - Power & Electronics: Always-on architecture with UPS backup; 3D-printed PLA housings with BMP388 thermal sensor and cooling fans ($35\,^\circ\text{C}$ on / $32\,^\circ\text{C}$ off).

2. **Literature & Citations Added (`References/references.bib` and Chapter 2):**
   - `Ding2022`: Pak choi sigmoidal logistic leaf expansion in greenhouses ($R^2 > 0.98$).
   - `Cho2015`: Expolinear growth for pak choi fresh/dry weight ($R^2 = 0.982$).
   - `Hosoda2024`: Multi-day early image time-series forward projection of fresh weight ($R^2 = 0.885$).
   - `Kim2022`: Projected canopy area predicting biomass under variable irrigation ($R^2 = 0.74$).
   - `Lee2024`: Vegetation fraction and soil moisture co-modeling for *Brassica rapa*.

3. **Appendices Harmonized:**
   - Appendix 4 (BOM): 9 capacitive sensors, 9 solenoid valves, Camera Module 3, BMP388, cooling fans.
   - Appendix 6 (WBS): 30-day grow-out timeline.
   - Appendix 7 (Vision Pseudocode): Exposure convergence to $V=73$, Voronoi cell masking, $3 \times 3$ opening.
   - Appendix 8 (CSV Log Structure): Includes `Cell GPR` and 30-day timeline.

4. **Compilation & Live Preview Tooling:**
   - Standalone compiler `tectonic` configured for both XeTeX and pdfLaTeX compatibility.
   - Quick compile script: `./compile.sh` compiles the full 78-page document in ~5 seconds.
   - Auto-watch daemon: `python3 auto_watch.py` automatically recompiles `thesis.pdf` whenever any `.tex` or `.bib` file is saved.

---

## What is still to do (Run 2 Harvest & Final Wrap-Up)

1. **Chapter 4 (Results & Discussion):**
   - Days 1 to 12 data is already integrated (90 rows written, D2–D3 outage transparently reported).
   - Once Run 2 completes and is harvested on **Day 30 (November 27, 2026)**, drop in the harvest fresh weights (`harvest_weights.csv`) into `analyze_yield.py` to fill the `\pending{}` sections:
     - Final harvest fresh weights table
     - Fitted 6-term polynomial equation with numerical coefficients ($\beta_0$ to $\beta_5$)
     - LOOCV $R^2$ score and MAE (grams)
     - Residual plots per treatment group
2. **Chapter 5 (Conclusions and Recommendations):**
   - Synthesize RQ1–RQ3 findings and future work once Chapter 4 numbers are finalized.
3. **Front Matter (Abstract & Acknowledgment):**
   - Draft together at the end. Keep acknowledgment within 1–2 pages.
4. **Day 0 pH Table:**
   - Measure soil pH at harvest or document omission in Section 4.

## Who writes what

The project is split per file precisely so three people can work at once.

| Part | Owner |
|---|---|
| Ch1 Introduction, Ch2 Literature | Kent |
| Ch3 hardware sections, hardware appendices | Cedric |
| Ch3 agronomy sections, Ch4 growing environment | Rey |
| Ch4 vision and statistics, Ch5 | Kent |
| Abstract, Acknowledgment | Together, last |

One chapter per person per sitting. Two people in `chapter3.tex` at the same
time is the main way this gets messy.

## Rules from the meeting

- Blank pages are intentional. The layout is two-sided for hardbound printing. Leave them.
- Do not touch `Classes/` or `sty/`. Add packages only in `Preamble/preamble.tex`.
- Keep `\bibliographystyle{IEEEtran}` and the numbered citation style.
- `thesis.tex` is the main file. Do not rename it.
- The acknowledgment is the one place first person is allowed. One page, two at most. Thank the panel.
- The chapter count is not fixed at five. If Chapter 4 reads better split, do that and ask the advisers first.
- Keep figures in the chapter that uses them, not in one pooled folder.
