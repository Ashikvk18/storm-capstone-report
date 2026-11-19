# DEVLOG — why the pipeline is built the way it is

This document explains every function, variable, and non-obvious condition in
the RQ2 analysis pipeline: what it does and, more importantly, *why* it exists.
Read alongside the code; each entry names the file and the construct.

Pipeline order:

```
extract_zip.py        -> recovered/*.mp4 + *.vtt   (rescue damaged archive)
build_labels.py       -> data/labels.csv           (survey -> outcome scores)
segment_sessions.py   -> out/*_timeline.csv, *_framesig.csv, data/session_segments.csv
extract_face.py       -> out/*_face.csv, *_blend.csv (ML head pose + expressions)
extract_features.py   -> data/features.csv         (behavioral features)
explore.py            -> data/explore_correlations.csv (feature x outcome)
model_rq2.py          -> data/model_coefficients.csv   (LASSO + LOO-CV)
make_figures.py       -> figures/*.png             (report visuals)
make_pca.py           -> figures/pca_*.png         (behavior profiles)
make_pdf.py           -> storm-capstone.pdf        (README -> PDF)
```

---

