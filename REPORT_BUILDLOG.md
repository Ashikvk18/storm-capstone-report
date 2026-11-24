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
   into `report_figures/` and