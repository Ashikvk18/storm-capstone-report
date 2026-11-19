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

## Environment

- **Python 3.10+** (developed on 3.13, Windows)
- Core: `opencv-python`, `pandas`, `numpy`, `matplotlib`, `scipy`
- Modeling: `scikit-learn`
- Face analysis: `mediapipe` (Tasks API)
- Labels: `openpyxl` (Qualtrics `.xlsx` exports)
- PDF: `fpdf2`

No GPU required — MediaPipe FaceLandmarker runs on CPU at ~1 fps
sampling, which keeps the whole face pass at roughly 3 min per recording.

## Required inputs (not in the repo)

| Input | Where it comes from | Used by |
|---|---|---|
| `VR_Training_Zoom_Recordings.zip` | Study recordings archive | `extract_zip.py` |
| Pre-survey `.xlsx` | Qualtrics export | `build_labels.py` |
| Post-survey `.xlsx` | Qualtrics export | `build_labels.py` |
| `data/participants.csv` | Manually built name↔PID↔file map | `extract_features.py` |
| `face_landmarker.task` | MediaPipe model URL (in `extract_face.py` docstring) | `extract_face.py` |

Raw recordings, transcripts, survey exports, and the participant map
contain PII and are `.gitignore`d — only derived, de-identified CSVs and
figures are committed.

### Input detail: recordings + transcripts

`recovered/` must contain one `.mp4` and (usually) one `.vtt` per
session, named consistently — the pipeline pairs them by filename
stem. Transcripts are Zoom auto-captions; speaker labels vary by
recording machine, so only the `"audio shared"` substring is trusted
to mark in-app narration.

Two known data-quality cases are expected, not bugs:

- **P04** — transcript begins ~4 min into the video; early phases are
  censored to NaN, not zero.
- **P07** — truncated MP4, no transcript; all phase features are NaN
  and `app_no_transcript_s` carries the usable duration.

### Input detail: `data/participants.csv`

Columns: `participant_id, name, email, recording_file, recording_date,
notes`. `recording_file` must match the MP4 filename stem in
`recovered/` (e.g., `2026-01-20_StorM_P02_Kamsi Amaeshi.mp4`). This file
is the only place real names appear in the pipeline and is gitignored.
