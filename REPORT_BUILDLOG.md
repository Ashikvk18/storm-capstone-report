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

7. **Fixed cropped figures.** The first PDF render showed clipped titles
   and labels: every `savefig` call lacked `bbox_inches="tight"`. Patched
   `make_figures.py`, `make_pca.py`, and `make_expr_timeline.py`, added
   `make_expr_gallery.py` for the cross-session expression figure,
   regenerated all six analysis figures, and re-rendered the PDF.

8. **Verified and pushed.** Ran `verify.py` (all checks pass), then pushed
   all commits to `origin/master`.

## Analysis figures and where they appear

| File | Type | Placed in report | Location in Section 1 |
|---|---|---|---|
| `figures/nav_vs_confusion.png` | Scatter: survival navigation time vs reported confusion | Between the damaged-archive recovery paragraph and the "Once the recordings were recovered" segmentation paragraph | Early in the detailed description, bridging data recovery and analysis |
| `figures/pca_confusion.png` | PCA of session behavior profiles, colored by confusion | After the "Finally, ... verification" paragraph — last image in Section 1 | Closes the detailed description alongside the findings discussion |
| `figures/expr_across_sessions.png` | Small multiples: four action units across six sessions