# Data Dictionary — committed CSVs

Column-by-column definitions for every de-identified dataset in `data/`.
Conventions used throughout:

- **`participant_id` (P01–P22)** — the only identifier ever committed;
  real names live only in gitignored `participants.csv`.
- **NaN ≠ 0** — a missing value means "unobserved" (truncated video,
  late transcript, face not detected), never "didn't happen."
- All durations are **seconds**; all timestamps are **seconds into the
  recording**.

## `features.csv` — one row per recorded session (20 rows)

Produced by `extract_features.py` from per-second timelines, frame
signatures, transcripts, and face/blend caches. Restricted to the
app-session window wherever noted.

| Column | Meaning |
|---|---|
| `participant_id` | PID joined via `participants.csv` |

### Timing columns (dwell per phase)

Seconds labeled with each phase inside the app window:
`lesson1_s, quiz1_s, lesson2_s, impacts_s, survival_call_s,
survival_nav_s, final_quiz_s` — the seven scripted content phases —
plus `pre_app_s, post_app_s, app_idle_s, aborted_s,
app_no_transcript_s, interview_s` for everything else.
`session_s` = first app frame → sustained-desktop/interview onset.

### Retry, quiz, and speech columns

| Column | Meaning |
|---|---|
| `survival_attempts` | Count of survival-call clusters (<10 s gaps merged) — P02=2, all others=1 |
| `was_restarted` | 1 if any `aborted` seconds exist (app restarted mid-recording; P15) |
| `speech_in_session_s` | Participant utterance seconds inside the session window |
| `reached_end` | 1 if the session reached final quiz / post-app / interview |
| `quiz1_correct`, `quiz1_wrong`, `finalq_correct`, `finalq_wrong` | Spoken feedback counts inside each quiz window |

### Webcam and frame motion columns

| Column | Meaning |
|---|---|
| `webcam_motion_mean` | Mean per-second pixel change in the webcam corner |
| `webcam_still_ratio` | Fraction of session seconds below the stillness threshold (1.2) |
| `webcam_longest_still_s` | Longest continuous still streak |
| `cam_motion_lessons` / `cam_motion_survival_nav` | Same motion metric split: passive lessons vs. active navigation |
| `frame_motion_mean` | Whole-frame motion — confounded with scripted animation; excluded from modeling |

### Head-pose columns (MediaPipe FaceLandmarker)

| Column | Meaning |
|---|---|
| `face_detect_ratio` | Fraction of session seconds a face was found |
| `head_yaw_std`, `head_pitch_std` | Spread of head rotation (movement amount) |
| `head_turn_rate` | Mean per-second angular change |
| `pitch_mean` | Mean head pitch (camera-mount sensitive) |
| `look_away_ratio` | Fraction of detected seconds deviating >25° yaw or >20° pitch from the participant's own median pose |

### Expression columns (facial action units)

Session aggregates of per-second blendshape scores, symmetric
Left/Right pairs averaged. All values 0–1 activation.

| Column | Action units averaged |
|---|---|
| `expr_smile_mean`, `expr_smile_max` | mouthSmile Left/Right |
| `expr_frown_mean` | mouthFrown Left/Right |
| `expr_brow_up_mean`, `expr_brow_up_max` | browInnerUp + browOuterUp L/R |
| `expr_blink_mean` | eyeBlink Left/Right |
| `expr_jaw_mean` | jawOpen |
| `expr_sneer_mean` | noseSneer Left/Right |
| `expr_stretch_mean` | mouthStretch Left/Right |

`*_max` columns are single-frame-sensitive — treat as fragile.

### Data-quality flag columns

| Column | Meaning |
|---|---|
| `no_transcript` | 1 if the recording has no usable transcript (P07) — all phase features then NaN |
| `transcript_gap` | 1 if `pre_app` >120 s with zero lesson1 seconds (P04's late-starting transcript) — early phases censored to NaN |

## `labels.csv` — survey-derived outcomes (~22 rows)

Produced by `build_labels.py` from the pre/post Qualtrics exports.
Includes survey-only respondents (`has_recording`=0) who have no video.

### Knowledge scores

| Column | Meaning |
|---|---|
| `pre_score`, `post_score` | 10-point tornado-knowledge scores (8 binary MC + drag-drop matching + sequencing, partial credit) |
| `learning_gain` | `post_score − pre_score` |

### Self-report composites (post-survey only)

| Column | Meaning | Scale |
|---|---|---|
| `engagement` | Six GUESS items (focus/engrossment/motivation; "bored" reverse-coded), α≈.85 | 1–7 |
| `confusion` | Four cognitive-load items on unclear/ineffective explanations, α≈.80 | 0–10 |
| `perceived_learning` | Four cognitive-load items on perceived learning | 0–10 |
| `effort` | Two cognitive-load items on invested effort | 0–10 |
| `complexity` | Three cognitive-load items on content complexity | 0–10 |
| `guess_full` | All 18 GUESS items, one reverse-coded | 1–7 |
| `has_recording` | 1 if a session recording exists for this participant | 0/1 |

Confusion has a floor effect (6/19 exact zeros); `explore.py` adds a
binary `confusion_any` target at analysis time.

## `session_segments.csv` — per-phase spans (20 rows)

Produced by `segment_sessions.py`. For every phase label, three
columns: `<phase>_t_start`, `<phase>_t_end`, `<phase>_t_dur` (seconds).
Phases include the seven content phases plus `pre_app, post_app,
app_idle, aborted, app_no_transcript, desktop, interview,
participant_speech`. `pid` and `duration_s` (total recording length)
lead the row. Multiple spans of the same phase are merged into
first-start/last-end/total-duration.

## `explore_correlations.csv` — correlation screen (~120 rows)

Produced by `explore.py`. One row per feature×target pair with ≥8
valid observations.

| Column | Meaning |
|---|---|
| `target` | Outcome: engagement, confusion, confusion_any, effort, complexity, perceived_learning, guess_full, post_score, learning_gain |
| `feature` | Behavioral feature name (same names as `features.csv`) |
| `n` | Valid paired observations (17–19 typical) |
| `rho` | Spearman rank correlation, rounded to 3 decimals |
| `p` | Two-sided p-value, rounded to 4 decimals — uncorrected for multiple testing |

## `model_coefficients.csv` — LASSO audit trail (~78 rows)

Produced by `model_rq2.py`. One row per feature×regression-target.

| Column | Meaning |
|---|---|
| `target` | `engagement` or `confusion` (continuous LASSO targets only) |
| `feature` | Behavioral feature name |
| `selected_folds` | In how many of 19 leave-one-out folds the feature's coefficient was non-zero |
| `median_coef` | Median standardized coefficient across folds |

A feature selected in ≤2 folds is noise; the honest result is that
almost nothing was selected consistently.
