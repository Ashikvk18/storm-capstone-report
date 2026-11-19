# Reproducibility Appendix — RQ2 Video-Observation Pipeline

This appendix lets an independent researcher rebuild every number and
figure in the RQ2 analysis from the raw inputs. It complements:

- **`DEVLOG.md`** — *why* each function, variable, and condition exists
- **`RQ2_report_section.md`** — the findings written up for the report
- **`README.md`** — project overview and quick-start

Everything below uses participant IDs (P01–P22) only; names and emails
never enter the repository.

## Pipeline order

```
VR_Training_Zoom_Recordings.zip  (damaged ~5 GB archive)
        |
        v
extract_zip.py          -> recovered/*.mp4 + *.vtt     [step 1]
segment_sessions.py     -> out/*_timeline.csv           [step 2]
                        -> out/*_framesig.csv  (cached)
                        -> data/session_segments.csv
extract_face.py         -> out/*_face.csv               [step 3]
                        -> out/*_blend.csv   (cached)
extract_features.py     -> data/features.csv            [step 4]
build_labels.py         -> data/labels.csv              [step 5]
explore.py              -> data/explore_correlations.csv[step 6]
model_rq2.py            -> data/model_coefficients.csv  [step 7]
make_figures.py         -> figures/ (3 PNGs)            [step 8]
make_pca.py             -> figures/pca_*.png            [step 9]
make_expr_timeline.py   -> figures/p02_expressions.png  [step 10]
make_pdf.py             -> storm-capstone.pdf           [step 11]
```

Steps 1–5 must run in order (each consumes the previous step's output).
Steps 6–11 can run in any order once 1–5 are complete.
