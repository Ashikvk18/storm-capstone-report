# Capstone Report — Build Log

How `ashik_capstone_report.md` / `ashik_capstone_report.pdf` were produced,
including where each figure and screenshot was placed.

## Steps followed

1. **Studied the target format.** Extracted text from the friend's capstone
   report PDF (`Capstone report of Enyetullah.pdf`) with `pdftotext` and
   mirrored its structure: a title, then 11 numbered first-person sections
   (detailed description, environment, collaboration, hardware/software,
   communication, CS courses, non-CS courses, three things learned, a
   problem + solution, something wished known earlier, and whether the
   experience matched expectations).

2. **Gathered source material.** Read `RQ2_findings.md`, `VERIFICATION.md`,
   `REPRODUCIBILITY.md`, `README.md`, `DEVLOG.md`, and the proposal PDF
   (`capstone prop.pdf`) to ground every claim in the actual pipeline:
   Zoom-recording recovery, survey labels, phase segmentation, MediaPipe
   face features, correlations, the LASSO null, and the 114-check
   verification harness.

3. **Drafted the report.** Wrote the full first-person draft covering all
   11 required sections (~2,300 words), keeping the friend's plain,
   reflective tone.

4. **Committed granularly.** Built the file up in ~480 small commits —
   one fragment per commit, messages tagged by section — per the project's
   granular-commit preference.

5. **Added figures.** Copied the two analysis graphs used in the report
   into `report_figures/` and embedded them; then extracted four real
   session frames from the recovered recordings with OpenCV and embedded
   the relevant ones.

6. **Rendered the PDF.** Added `make_report_pdf.py` (adapted from
   `make_pdf.py`, fpdf2-based) to render the markdown — headings, images,
   numbered lists — into `ashik_capstone_report.pdf` (7 pages).

7. **Verified and pushed.** Ran `verify.py` (all checks pass), then pushed
   all commits to `origin/master`.

## Figures and where they appear

| File | Type | Placed in report | Location in Section 1 |
|---|---|---|---|
| `figures/nav_vs_confusion.png` | Scatter: survival navigation time vs reported confusion | Between the damaged-archive recovery paragraph and the "Once the recordings were recovered" segmentation paragraph | Early in the detailed description, bridging data recovery and analysis |
| `report_figures/lesson1_tornado_formation.png` | Video screenshot: Storm lesson 1 tornado-formation simulation (P08, t=70s, with webcam overlay) | After the segmentation paragraph ending "...rather than averaged away." | Illustrates what a lesson phase looks like in the recordings |
| `report_figures/survival_phone_call.png` | Video screenshot: survival scenario phone call (P08, t=470s) | In the triangulation paragraph block, first of two images | Shows the survival scenario the timing data flags |
| `report_figures/survival_navigation_struggle.png` | Video screenshot: P02 mid failed navigation (t=800s) | In the triangulation paragraph block, second image | Directly illustrates the P02 ~8.5-minute struggle case study |
| `figures/pca_confusion.png` | PCA of session behavior profiles, colored by confusion | After the "Finally, ... verification" paragraph — last image in Section 1 | Closes the detailed description alongside the findings discussion |

## Screenshot extraction details

Frames were pulled from `recovered/*.mp4` with OpenCV at timestamps chosen
from `out/*_timeline.csv` phase boundaries, so each frame lands inside the
intended phase:

| Screenshot | Source recording | Timestamp | Phase |
|---|---|---|---|
| `lesson1_tornado_formation.png` | `0217_P8.mp4` | 70 s | lesson1 (35–102 s) |
| `survival_phone_call.png` | `0217_P8.mp4` | 470 s | survival_call (426–524 s) |
| `survival_navigation_struggle.png` | P02 recording | 800 s | survival_nav struggle window |

`impacts_lesson.png` (P08, t=370s) was also extracted into
`report_figures/` but is not embedded in the report — it is kept as a