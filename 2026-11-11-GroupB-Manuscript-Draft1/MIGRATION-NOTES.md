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

## What is still yours to do

### 1. The tense pass

The only thing Maam Antoi named directly when asked whether Chapters 1 to 3
could carry over. The proposal is in future tense because nothing had been
built. Past tense for what was done, present tense for established facts.

### 2. Content corrections that are overdue

These were true in the proposal and are not true of the system you built.

| Where | Proposal says | Reality |
|---|---|---|
| Ch1 scope, Ch3 | Bulk commercial potting mix from the Department of Agriculture | Garden soil, rice hull and vermicast at 8:4:3, batch-mixed |
| Ch1 Table 1.1 | 315-row dataset, 35-day cycle | 30-day cycle; row count depends on the reported run |
| Ch1 Table 1.1 | Day 0 pH measurement table for 9 pots | Never measured. Either drop the deliverable or measure at harvest and say when |
| Ch3 | Pot of 200 mm upper diameter | 13 cm |
| Ch3 | Raspberry Pi Camera Module V2, 62.2 x 48.8 degrees | Camera Module 3 (imx708), 1296 x 1296 capture |
| Ch3 | 350 mm pitch, 900 mm array, 1100 mm camera elevation | Recompute from the 13 cm pot and the measured height |
| Ch3 | ESP32-S3 drawing 80 mA in deep-sleep polling | Always-on architecture. The sentence contradicts itself |
| Ch3, Ch1 | GPR computed over a fixed circular ROI | A non-overlapping per-pot area: each pot claims the pixels nearest its own centre, out to a capped radius |
| Ch3 | Greenhouse with a fixed overhead LED array for standardised illumination | Timber-framed enclosure, UV plastic and mesh, natural light only, brightness-normalised exposure |
| App D | BOM lists 4 sensors, 4 valves, Camera V2 | 9 sensors, 9 valves, Camera Module 3 |
| App G | HSV threshold written as `35 <= Hue <= 85` in degrees | Hue 38 to 85 in OpenCV units (0 to 179), S >= 100, V >= 55 |
| App G | Pseudocode applies bounding coordinates per pot | Applies the per-pot area, then a 3x3 morphological opening |

### 3. The gap the panel already asked about

Section 3.5, "System Calibration and Pre-Deployment Validation", has five items:
sensor calibration, cron and storage test, illumination and HSV tuning, FOV and
ROI mapping, canopy overlap validation.

Every one validates the apparatus. None validates the measurement. Nothing shows
that a GPR number corresponds to anything real. That is what the panel's
question about validating the camera data was pointing at.

`Dual_Archi/tools/gpr_validate.py` already produces precision, recall, IoU,
Dice, automatic versus manual GPR, bias, Pearson r, Bland-Altman limits and
inter-annotator agreement. Add the method as a sixth item in Section 3.5 and the
results in Chapter 4, in the section already stubbed for it.

### 4. Chapter 2 references

Maam Antoi asked for new references to be added if you have found any since the
proposal. Add them to `References/references.bib` and cite by key.

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
