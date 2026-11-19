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

### Input detail: survey exports

Two Qualtrics `.xlsx` files (pre and post). `build_labels.py` expects
the exact filenames at the top of the script — rename or edit the
constants if your exports differ. The script drops Qualtrics' two
metadata rows, dedupes repeat pre-survey submissions, excludes
pilot/test rows by name, and fuzzy-matches survey names to PIDs.

### Input detail: `face_landmarker.task`

Download from:
`https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task`

Place it in the repo root. `extract_face.py` loads it via
`BaseOptions(model_asset_path="face_landmarker.task")`. The model is
~30 MB and is not committed.

## Step-by-step reproduction

### Step 1 — `extract_zip.py` (archive recovery)

```bash
python extract_zip.py            # all entries -> recovered/
python extract_zip.py P08        # or a substring for one file
```

The central directory of the study archive is corrupt, so this script
scans raw bytes for `PK\x03\x04` local headers, caches offsets to
`_zip_index.json`, and copies STORED (uncompressed) entry data while
stripping 12–16-byte data descriptors. Expect ~39 outputs (20 MP4 + 19
VTT). P07's MP4 will be truncated — that is the archive's damage, not
a script failure.

### Step 2 — `segment_sessions.py` (phase segmentation)

```bash
python segment_sessions.py       # all videos (~minutes; cached)
python segment_sessions.py P02   # or one recording substring
```

Fuses VTT narration landmarks with 1-fps frame signatures (white-pixel
desktop detection + frame/webcam motion). Writes `out/*_timeline.csv`
(per-second phase labels), caches `out/*_framesig.csv`, and appends
`data/session_segments.csv`. Runtime is dominated by video decode;
re-runs reuse the frame-signature cache.

### Step 3 — `extract_face.py` (ML face analysis)

```bash
python extract_face.py           # all videos (~3 min each)
python extract_face.py P08       # or one recording substring
```

MediaPipe FaceLandmarker on the top-right webcam crop at 1 fps.
Outputs `out/*_face.csv` (head pose: yaw/pitch/roll, face position,
width) and `out/*_blend.csv` (16 facial action-unit scores). Each file
is cached independently — a video needing only the missing half still
runs one pass. Expect ~1,400–3,500 rows per video; P09's blend/pose
coverage is near-zero because her webcam overlay was off during the
app.

### Step 4 — `extract_features.py` (behavioral features)

```bash
python extract_features.py       # -> data/features.csv (20 rows)
python extract_features.py P04   # or one recording substring
```

Joins timeline + framesig + transcript + face/blend caches into one
row per participant: phase durations, retries, quiz counts, speech,
webcam/frame motion, head pose, and expression aggregates. Missing
data stays NaN. Verify: 20 rows; P02 `survival_attempts`=2; P04 phase
columns NaN; P07 `no_transcript`=1.

### Step 5 — `build_labels.py` (survey labels)

```bash
python build_labels.py           # -> data/labels.csv
```

Requires the two survey `.xlsx` files present under their expected
filenames. Prints Cronbach's alpha for the engagement and confusion
composites (expect ≈.85 and ≈.80). Verify: `learning_gain` =
`post_score − pre_score`; `has_recording` flags survey-only rows.

### Step 6 — `explore.py` (correlation screen)

```bash
python explore.py                # -> data/explore_correlations.csv
```

Inner-joins features + labels (n≈19), adds the binary `confusion_any`
target, and computes Spearman ρ for every feature×target pair with
≥8 valid observations. Prints top-10 per target; writes the full table
(≈120 rows). Expect the headline rows: `look_away_ratio→effort`
ρ=−.64, `expr_frown_mean→confusion` ρ=+.57, `lesson1_s→post_score`
ρ=+.51.
