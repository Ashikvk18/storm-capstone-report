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

### Step 7 — `model_rq2.py` (LASSO + LOO-CV)

```bash
python model_rq2.py              # -> data/model_coefficients.csv
```

Standardized LASSO with leave-one-out CV and inner 5-fold alpha
selection, plus L1 logistic regression for `confusion_any`. Reports
LOO R²/accuracy vs mean/majority baselines and per-feature selection
frequency. Expected result is the honest null: R² < 0, accuracy at or
below baseline.

### Step 8 — `make_figures.py` (report figures)

```bash
python make_figures.py           # -> figures/*.png (3 files)
```

P02 phase timeline, lesson1-vs-post-score scatter, and
nav-time-vs-confusion scatter. Participant IDs (not names) are
annotated so the PNGs are safe to commit.

### Step 9 — `make_pca.py` (behavior-profile PCA)

```bash
python make_pca.py               # -> figures/pca_*.png (2 files)
```

Standardizes a 10-feature behavior subset and projects to 2 PCs
(PC1≈48 %, PC2≈21 % of variance), plotted twice — colored by
engagement and by confusion.

### Step 10 — `make_expr_timeline.py` (P02 expression case study)

```bash
python make_expr_timeline.py     # -> figures/p02_expressions.png
```

15-second-smoothed facial action units (frown, brow-raise, smile,
jaw-open) over P02's phase bands, with the scenario-replay and
failed-navigation windows annotated.

### Step 11 — `make_pdf.py` (report PDF)

```bash
python make_pdf.py               # README.md -> storm-capstone.pdf
```

Minimal markdown→PDF renderer (fpdf2). Regenerate whenever `README.md`
changes; it embeds the three `make_figures.py` PNGs inline.

### Step 12 — `verify.py` + `verify_transcripts.py` (verification)

```bash
python verify.py               # 52 checks on committed CSVs/artifacts
python verify_transcripts.py   # 62 checks on raw VTT/MP4 inputs
```

`verify.py` re-checks structure, anomaly spot-values, every correlation,
model sanity, figure/PDF integrity, and PII hygiene — exits non-zero
on failure. `verify_transcripts.py` audits the raw transcripts:
cue counts, landmark presence, duration bounds, phase play-order, and
survival-call coverage. See `VERIFICATION.md` for the full report and
`verification_output.txt` / `transcript_verification_output.txt` for
captured runs.

## Output artifacts

| Artifact | Producer | Rows / pages | Contents |
|---|---|---|---|
| `data/session_segments.csv` | segment_sessions | 20 | per-phase start/end/duration per session |
| `data/features.csv` | extract_features | 20 × ~46 | all behavioral features (see `data/DATA_DICTIONARY.md`) |
| `data/labels.csv` | build_labels | ~22 | survey composites + knowledge scores |
| `data/explore_correlations.csv` | explore | ~120 | every feature×target Spearman result |
| `data/model_coefficients.csv` | model_rq2 | ~78 | LASSO selection frequency + median coef |
| `figures/*.png` | make_figures / make_pca / make_expr_timeline | 6 | report visuals |
| `storm-capstone.pdf` | make_pdf | 4 pages | README rendered with figures |
| `out/*_timeline.csv` | segment_sessions | per-second | phase label per second (cached) |
| `out/*_framesig.csv` | segment_sessions | per-second | desktop flag + motion (cached) |
| `out/*_face.csv` / `*_blend.csv` | extract_face | per-second | head pose / action units (cached) |

## Verification checklist

After a full run, confirm:

1. **Counts** — `features.csv` has 20 rows; `labels.csv` has ~22 rows
   (includes survey-only respondents); `explore_correlations.csv` has
   ~120 rows.
2. **Spot checks** — P02 `survival_attempts` = 2; P04 lesson phases are
   NaN (not 0); P07 `no_transcript` = 1; P15 `was_restarted` = 1.
3. **Headline correlations reproduce** — `look_away_ratio→effort`
   ρ ≈ −.64; `expr_frown_mean→confusion` ρ ≈ +.57;
   `lesson1_s→post_score` ρ ≈ +.51.
4. **Model null reproduces** — engagement LOO R² ≈ −.20, confusion
   R² ≈ −.13, `confusion_any` accuracy ≈ .63 < .74 baseline.
5. **Figures regenerate** — all six PNGs and the 4-page PDF produce
   without error.

## Troubleshooting

- **Truncated video (P07)** — OpenCV/ffmpeg report "partial file";
  expected. The pipeline labels its usable seconds `app_no_transcript`
  and continues.
- **Stale caches** — `*_framesig.csv` from before the motion columns
  existed is auto-detected (missing `cam_motion`) and recomputed;
  delete `out/*_framesig.csv` to force a fresh decode.
- **MediaPipe API names** — this project pins the Tasks API:
  `output_face_blendshapes=True` (option) and `res.face_blendshapes`
  (result). Older guesses (`output_facial_blendshapes`,
  `facial_blendshapes`) raise TypeError/AttributeError.
- **Name leakage** — filenames contain real names; every committed
  artifact must use `participant_id`. `participants.csv` and survey
  exports stay local.

## Pointers

- **`DEVLOG.md`** — per-construct rationale: why each threshold, guard,
  and merge rule exists.
- **`RQ2_findings.md`** — detailed analysis write-up with all tables.
- **`RQ2_report_section.md`** — the report-ready chapter.
- **`data/DATA_DICTIONARY.md`** — column-by-column definitions for every
  committed CSV.

*Reproducibility appendix — Storm capstone, RQ2 (Ashik Dey Rupak).*
