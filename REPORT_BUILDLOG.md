# Capstone Report — Build Log

How `ashik_capstone_report.md` / `ashik_capstone_report.pdf` were produced,
including where each figure, graph, and screenshot was placed.

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
   11 required sections (~2,400 words), keeping the friend's plain,
   reflective tone.

4. **Committed granularly.** Built the file up in ~500 small commits —
   one fragment per commit, messages tagged by section — per the project's
   granular-commit preference.

5. **Added figures.** Copied the two analysis graphs used in the report
   into `report_figures/` and embedded them; then extracted session frames
   from many different participant recordings with OpenCV — not just one
   video — and embedded a six-participant phase gallery plus the P02 case
   study frame.

6. **Rendered the PDF.** `make_report_pdf.py` (adapted from `make_pdf.py`,
   fpdf2-based) renders the markdown — headings, images, numbered lists —
   into `ashik_capstone_report.pdf`.

7. **Verified and pushed.** Ran `verify.py` (all checks pass), then pushed
   all commits to `origin/master`.

## Analysis figures and where they appear

| File | Type | Placed in report | Location in Section 1 |
|---|---|---|---|
| `figures/nav_vs_confusion.png` | Scatter: survival navigation time vs reported confusion | Between the damaged-archive recovery paragraph and the "Once the recordings were recovered" segmentation paragraph | Early in the detailed description, bridging data recovery and analysis |
| `figures/pca_confusion.png` | PCA of session behavior profiles, colored by confusion | After the "Finally, ... verification" paragraph — last image in Section 1 | Closes the detailed description alongside the findings discussion |

## Session screenshots — extraction details

Frames were pulled from `recovered/*.mp4` with OpenCV at the **median
timestamp of each phase** from `out/*_timeline.csv`, so every frame lands
inside the intended phase. Thirteen frames were extracted from **thirteen
different participant recordings**:

| File | Participant | Phase | Timestamp |
|---|---|---|---|
| `report_figures/session_p12_lesson1.png` | P12 | lesson1 | 70 s |
| `report_figures/session_p14_lesson2.png` | P14 | lesson2 | 291 s |
| `report_figures/session_p10_impacts.png` | P10 | impacts | 389 s |
| `report_figures/session_p05_quiz1.png` | P05 | quiz1 | 169 s |
| `report_figures/session_p11_survival_call.png` | P11 | survival_call | 475 s |
| `report_figures/session_p09_survival_nav.png` | P09 | survival_nav | 595 s |