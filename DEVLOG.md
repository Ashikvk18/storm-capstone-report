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

## extract_zip.py — rescuing a corrupted archive

The source `VR_Training_Zoom_Recordings.zip` (~5 GB) has a broken central
directory, so `zipfile` cannot open it. Entries are STORED (uncompressed)
with sizes in a trailing data descriptor — file data simply runs from each
local header to just before the next one, minus 12–16 descriptor bytes.

| Construct | Why |
|---|---|
| `ZIP_PATH`, `INDEX_PATH`, `OUT_DIR`, `DD_SIG` | Archive location, cache of the header scan (re-scanning 5 GB is slow), output folder, and the `PK\x07\x08` signature that marks a data descriptor. |
| `build_index()` | Scans the raw bytes for `PK\x03\x04` local-file-header signatures and records each entry's name + offsets. Reads in 64 MB chunks with a 400-byte `overlap` buffer because a header can straddle a chunk boundary — without the overlap, headers at chunk edges would be silently missed. |
| dedupe loop in `build_index()` | The overlap makes the same header visible in two chunks; `seen`/`uniq` drops the duplicate so each file is extracted once. |
| `data_end(f, next_offset)` | Decides where file data ends by checking whether the 4 bytes before the next header are the `PK\x07\x08` descriptor signature: 16-byte descriptor if present, else 12. Getting this wrong truncates or overruns every file. |
| `extract_entry()` | Copies bytes `[start, end)` in 8 MB chunks. Chunked because some videos are >1 GB — reading it all at once would blow memory. |
| last-entry special case in `main()` | There is no "next header" for the final entry, so the end is `zip_size` minus a possible trailing descriptor — checked directly at EOF. |
| `INDEX_PATH` cache | The 5 GB scan takes minutes; caching offsets to `_zip_index.json` makes re-extraction instant. |

## build_labels.py — survey answers -> outcome scores

| Construct | Why |
|---|---|
| `GUESS_MAP` | Maps the GUESS engagement survey's Likert *text* labels to 1–7. Includes `"strongy agree"` — a typo in the actual survey data that would otherwise silently score NaN. |
| `ENGAGEMENT_ITEMS = {"3","5","6","8","13","14"}` | The six GUESS items that measure focus/engrossment/motivation. Item 8 ("I feel bored") is **reverse-coded** — agreement means *less* engagement, so a high raw score must be flipped or the composite would be backwards. |
| `GUESS_REVERSED = {"8"}` | Same reverse-coding applied when scoring the full GUESS scale. |
| `CONFUSION_ITEMS = ["5"–"8"]` | The cognitive-load items asking whether explanations were unclear/ineffective — this composite is the "confusion" label. |
| `COMPLEXITY_ITEMS`, `PERCEIVED_LEARNING_ITEMS`, `EFFORT_ITEMS` | Other cognitive-load item groups kept as auxiliary outcomes so correlations can be checked against more than one label. |
| `EXCLUDE_NAMES` | Drops pilot/test rows (`test`, `testing`, `prabeen giri`) — researcher submissions that aren't real participants. |
| `load_qualtrics()` | `iloc[2:]` skips Qualtrics' two metadata rows (question text + import IDs) that would otherwise be scored as a respondent. |
| `norm_name()` / `to_pid()` | Survey names have typos vs. the recording list; fuzzy matching (`difflib`, cutoff 0.7) recovers the correct participant instead of dropping the row. |
| `guess_score()` | `8 - score` implements reverse coding for item 8; returns NaN (not 0) for missing answers so composites use `nanmean` and don't treat "unanswered" as "strongly disagree". |
| `cl_score()` | Cognitive-load items use anchor labels ("not at all"/"moderately"/"completely") instead of numbers; the prefix check maps them to 0/5/10 before falling back to float parsing. |
| `mc_correct()` | Substring matching because pre/post survey MC options are lettered differently between the two forms — the *content* is what matters. |
| `score_matching()` / `score_sequence()` | The drag-drop and re-sequence items are scored as *fraction correct* (of 3 terms / 4 stages), giving partial credit instead of all-or-nothing. |
| `knowledge_score()` | Combines 8 binary MC items + 2 fractional items = a 10-point knowledge score. `nansum` skips unanswered items rather than failing the whole score. |
| `MC_KEY` / `POST_COL` | The correct-answer substrings for each MC item, plus the column remap (`K1`→`Q2` etc.) because pre and post surveys number questions differently. |
| `cronbach_alpha()` | Internal-consistency reliability of the engagement/confusion composites — printed at runtime so we can report whether the labels are trustworthy (printed: engagement α≈.85, confusion α≈.80). |
| dedupe `pre` by name | Some participants submitted the pre-survey twice; `drop_duplicates(keep="first")` keeps the earliest submission. |
| `_key` join via `participant_id` | Joins pre and post rows on participant id (falling back to normalized name for survey-only respondents) — tolerates name typos *between* the two surveys. |
| `has_recording` | Flags survey respondents who have no video (e.g., P17 missing post-survey is handled on the label side). |
| `learning_gain = post - pre` | The learning outcome for RQ2 context. |
| dropping `survey_name` from output | PII — names/emails must not be committed; `participants.csv` stays local via `.gitignore`. |

## segment_sessions.py — cutting videos into phases

| Construct | Why |
|---|---|
| `SAMPLE_SEC = 1.0` | All frame analysis runs at 1 fps — enough temporal resolution for phase boundaries, cheap enough to decode 20 long videos. |
| `DESKTOP_WHITE = 0.60` | Threshold on the fraction of near-white pixels. Empirically, the brightest app scene (sky) reaches ~0.48 while Windows desktop/browser windows exceed 0.6 — this is the app-vs-desktop discriminator. |
| `MIN_SEG = 3` | Segments shorter than 3 s are dropped from summaries — sub-second label flicker would otherwise create dozens of meaningless phase rows. |
| `LANDMARKS` | Ordered narration phrases that mark phase *starts*. Landmarks are trusted over keyword classification because narration is scripted and identical across participants; keywords appear inside other phases' narration and cause misclassification (the `anchor_phases` docstring explains this). |
| `SURVIVAL_KW` / `IMPACTS_KW` / `L2_KW` / `L1_KW` | Keyword sets for `classify_app_cue` — fallback phase guessing *only* for phases whose landmark never appears in that transcript. Without the `landmark_phases` guard, stray words like "warm, moist air" (spoken during lesson 1) would hijack the phase. |
| `QUIZ_FB` | Matches spoken "correct"/"incorrect"/"well done" feedback. |
| `parse_vtt()` | Parses WebVTT cues into `(start, end, speaker, text)`. The regex captures the timestamp line plus body; speaker is split on the first `": "` because Zoom labels speakers inline (`"Audio shared by X: text"`). |
| `classify_app_cue()` | Keyword → phase guess. Order matters: survival keywords checked first (most distinctive), quiz feedback requires `len(t) < 60` so a long narration containing "correct" isn't misread as feedback. |
| `anchor_phases()` | The core state machine. Walks app-audio cues in order, promoting `cur` when a landmark (or guarded fallback) names a later phase. Two subtle conditions: **(a)** backward landmark → the app was *restarted* (P15): everything labeled so far is relabeled `aborted` so the fragment can't contaminate timings; **(b)** after labeling, cues inside the survival window that occur after the last keyword-bearing dialogue cue become `survival_nav` — game music/SFX kept emitting "Audio shared" cues through navigation, and the call replay (>20 s silence gap) is bridged as `survival_nav` so retries appear as separate call clusters. |
| `CAM_X0..CAM_Y1` | The Zoom webcam overlay occupies the top-right ~20%×15% of every frame — these bounds crop it for motion/face analysis. |
| `frame_flags()` | Per-second frame signature `(t, is_desktop, frac_orange, frame_motion, cam_motion)`. `frac_white` flags desktop; `frac_orange` (HSV hue<20, sat>120) detects the app's orange UI elements; `frame_motion`/`cam_motion` are mean-abs-diff vs previous frame — whole-screen activity and webcam-corner movement respectively. Results are cached to `*_framesig.csv` because re-decoding 20 videos is the expensive step; a **v1-cache check** (`cam_motion` column) forces recompute for caches written before motion columns existed. |
| `desktop_onset(frames, sustain=30)` | Finds the first second where desktop persists ≥30 s. Needed because stray "Audio shared" transcript cues (interview chit-chat misattributed to shared audio) appear *after* the app closes — the frame stream is the trustworthy session boundary. This fixed the P09 bug where the session window stretched to the full video. |
| `build_timeline()` | Builds the per-second label vector. Order of operations matters: **(1)** desktop frames labeled first; **(2)** non-app speech labeled `participant_speech` (inside app window) or `interview` (after); **(3)** app cues fill phases but can never overwrite `protected` labels (desktop/interview/speech); **(4)** each phase is extended forward to the next phase start so gaps between cues inherit the current phase — *except* `aborted` runs, whose gaps stay `app_idle`; **(5)** if there are no app cues at all (P07, no transcript), every non-desktop second becomes `app_no_transcript` rather than being silently zeroed; **(6)** remaining `app_idle` seconds before the first cue → `pre_app`, after the last → `post_app`. |
| `segments()` | Collapses the per-second vector into `(phase, start, end)` runs ≥ `MIN_SEG`. |
| `main()` | Per video: pick the `.vtt` (two possible suffixes), split cues into app audio (`"audio shared"` in speaker — Zoom's label for the shared app audio) vs. other speakers, compute frames, bound app cues at `desktop_onset`, segment, write `*_timeline.csv` + a summary row to `data/session_segments.csv` (with `pid` extracted from the filename — the raw filename contains names, so only `pid` is stored). |

## extract_face.py — ML features from the webcam overlay

MediaPipe FaceLandmarker (a pre-trained neural net) runs at 1 fps on the
top-right webcam crop. Two outputs per second: head pose → `*_face.csv`,
facial blendshapes (action units) → `*_blend.csv`.

| Construct | Why |
|---|---|
| `BLEND_KEYS` | The 16 action units worth tracking, chosen by construct: brows (confusion/surprise), blinks (drowsiness/effort), jaw/mouth (smile/frown/pucker/stretch = expression valence), nose sneer + cheek puff (negative affect). MediaPipe emits 52 blendshapes; these are the interpretable subset. |
| `head_pose()` name is historical | The function now emits both pose and blendshapes — the name predates the blendshape pass. |
| `need_pose` / `need_blend` cache checks | Each output has its own cache file; a video can need one pass but not the other (e.g., pose CSV exists from before blendshapes were added). Both are skipped independently — this is what lets the blendshape batch re-run only the missing half. |
| `output_facial_transformation_matrixes=True` | Requests the 4×4 head-pose matrix; without it `facial_transformation_matrixes` is empty. |
| `output_face_blendshapes=True` | The correct API name (an earlier `output_facial_blendshapes` guess raised `TypeError`). Requests the 52 action-unit scores. |
| Euler extraction | `yaw = atan2(m[2][0], m[0][0])`, `pitch = asin(-m[2][1])`, `roll = atan2(m[0][1], m[1][1])` — converts the rotation matrix to degrees. These approximate head orientation, **not** gaze. |
| `cx`, `cy`, `fw` | Face centroid and face width in pixels — proxies for how centered/close the participant sits to the webcam (posture/attention). |
| `res.face_blendshapes[0]` | Correct result attribute (an earlier `facial_blendshapes` guess raised `AttributeError`). Blendshape scores are 0–1 activations. |
| `(t, 1) + (0.0,)*len(BLEND_KEYS)` / `(t, 0) + (nan,)*...` | Keeps row length constant whether or not a face was detected — the CSV schema must not change mid-file. Missing frames get NaN (unknown), not 0 (no expression). |
| `except Exception` in `main()` | P07's MP4 is truncated; a decode error on one video must not kill the batch — it prints and continues. |

## extract_features.py — per-session behavioral features

| Construct | Why |
|---|---|
| `STILL_EPS = 1.2` | Mean-abs pixel diff below this counts as "still" webcam. Calibrated so normal breathing/subtle motion stays under it while real movement exceeds it. |
| `GAP_HEAD_S = 120` | `pre_app` longer than 2 min with zero `lesson1` seconds = the transcript started late (P04's VTT begins ~4 min in). Used to flag `transcript_gap`. |
| `APP_LABELS` / `PHASES` / `LESSON_PHASES` | `APP_LABELS` = every label meaning "app was on screen" (used to find the session's last second). `PHASES` = the 7 scripted content phases that get per-phase durations. `LESSON_PHASES` = the passive-content subset used for the lessons-vs-navigation motion contrast. |
| `CORRECT_RE` / `INCORRECT_RE` | Quiz feedback is spoken aloud; these regexes count it. `CORRECT_RE` requires "correct"/"well done" phrasing so narration mentioning the word doesn't count. |
| `parse_vtt()` | Same VTT parsing as segment_sessions, but keeps only `(start, end, text)` — speaker isn't needed for feedback counting. |
| `quiz_feedback(cues, t0, t1)` | Counts correct/incorrect cues overlapping a quiz window. Windowed so narration *about* quizzes elsewhere doesn't pollute the count. |
| `runs(tl, phase, merge_gap=10)` | Counts phase *attempts*. The merge matters: a 2-second `participant_speech` blip inside one survival call was splitting it into two "attempts" (the P05/P06 artifact). Runs separated by <10 s count as one attempt; P02's real retry (~570 s later) still counts as two. |
| `span(tl, phase)` | First/last second of a phase — used as the quiz-feedback window. |
| `transcript_gap` / `no_transcript` censoring | If a recording has no transcript (P07) or the transcript starts late (P04), unobserved phase durations are set to **NaN, not 0** — otherwise "we didn't see it" would be indistinguishable from "it didn't happen" and would corrupt every correlation. |
| session window (`s0`, `s1`) | `s0` = first non-desktop frame; `s1` = earliest of sustained-desktop onset or interview start. All subsequent features are restricted to this window so post-session survey-filling doesn't count as "behavior." |
| `speech_in_session_s` | Counts `participant_speech` seconds *within* `[s0, s1]` only — earlier versions counted the whole interview as "the participant talking." |
| `survival_attempts` / `was_restarted` | Attempt count via `runs()`; restart flag from `aborted_s > 0`. |
| `reached_end` | Whether the session reached the final quiz/post-app/interview — distinguishes "finished" from "abandoned." |
| quiz NaN handling | If a quiz window was never observed, its counts are NaN rather than 0. |
| `webcam_motion_mean`, `webcam_still_ratio`, `webcam_longest_still_s` | Motion-energy aggregates over the session window: average movement, fraction of still seconds, and the longest frozen streak (a candidate "checked out" indicator). |
| `cam_motion_lessons` vs `cam_motion_survival_nav` | Same motion metric computed separately over passive lessons and active navigation — the *contrast* is the signal (fidgeting during a movie vs. during gameplay mean different things). |
| head-pose block | Reads `*_face.csv`, restricts to `[s0, s1]`. `face_detect_ratio` = how often a face was found (data-quality + presence proxy). Yaw/pitch std = how much the head moved; `head_turn_rate` = mean per-second angular change. **`look_away_ratio` uses deviation from each participant's own median pose** (thresholds 25° yaw / 20° pitch) — camera mounting and hair cause systematic offsets (P05 reads −25° pitch all session), so absolute angles would flag her as "looking away" 100% of the time. Face-miss seconds are excluded — P09's webcam overlay was off during the app, which would otherwise read as constant look-away. The `len(vis) >= 60` guard requires ≥60 s of detected face before trusting the ratio. |
| blendshape block | Reads `*_blend.csv` within the same window, requires ≥30 detected seconds. Averages symmetric action units (e.g., `(mouthSmileLeft + mouthSmileRight)/2`) and emits interpretable aggregates: smile mean/max, frown, brow-up, blink rate, jaw openness, sneer, mouth stretch. All session-level — per-phase expression analysis is possible later but wasn't needed for the first pass. |
| `stem_to_pid` | Maps recording filenames to participant IDs via `participants.csv` — filenames contain real names (PII), so only `pid` is written to `features.csv`. |

## explore.py — correlation screen

| Construct | Why |
|---|---|
| `FEATURES` / `TARGETS` | The explicit feature and outcome lists — keeps the screen reproducible and makes it obvious which columns were tested (multiple-testing burden is ~84 tests at n≈19). |
| `confusion_any = (confusion > 0)` | The confusion composite has a floor effect (many exact zeros); the binary "any confusion" flag is a cleaner secondary target. |
| `ok.sum() < 8` guard | Skips feature×target pairs with fewer than 8 valid observations — a correlation on 5 points is meaningless. This is also why P07's all-NaN features silently drop out instead of corrupting results. |
| Spearman (not Pearson) | Features are skewed (e.g., `survival_nav_s` ranges 70–633 s) and several outcomes are ordinal composites — rank correlation is robust to both. |
| no multiple-testing correction | Deliberate: this is hypothesis-*generating* at n=19. The script prints raw p-values with the caveat in the docstring; `RQ2_findings.md` interprets them conservatively. |

## model_rq2.py — honest small-sample modeling

| Construct | Why |
|---|---|
| Feature exclusions | `frame_motion_mean` dropped (it's a proxy for time-in-animated-scenes, not a behavior); flag columns dropped; `was_restarted` dropped because it's positive for exactly 1/19 participants — nothing to learn from. |
| `ALPHAS = logspace(-2, 1.5, 40)` | LASSO penalty grid; wide enough to go from "keep everything" to "keep nothing." |
| `lasso_loo()` | Leave-one-out CV: for each held-out participant, pick alpha by *inner* 5-fold CV on the remaining 18, fit, predict. Nested CV is required — picking alpha on the full data then doing LOO would leak. |
| `selected` / `coefs` tracking | Counts in how many folds each feature was non-zero and the median coefficient — **stability across folds matters more than the point estimate** at n=19; a feature selected in 2/19 folds is noise. |
| `report_regression()` | Prints LOO R² vs. the mean-predictor baseline (R²=0). Features beating baseline = real signal; the actual result was R²<0 for both targets — reported honestly as a null. |
| `report_binary()` | L1 logistic regression for `confusion_any`, same LOO scheme, accuracy vs. majority-class baseline (0.74 — the model matched it exactly, i.e., learned nothing). |
| median imputation | `X_df.fillna(X_df.median())` — only P07's transcript-less row has NaNs; median imputation keeps her in the analysis for the features she does have. |
| `data/model_coefficients.csv` | Per-feature selection frequency + median coefficient — the audit trail behind "LASSO selected nothing." |

## make_figures.py — report visuals

| Construct | Why |
|---|---|
| `PHASE_ORDER` / `COLORS` | Fixed phase order and color map shared by the timeline figure and legend — keeps figures visually consistent. |
| `fig_p02()` | Draws P02's per-second phase labels as a single stacked bar (contiguous runs of identical labels merged). `desktop`/`interview` runs are skipped so the bar shows only the app window; the dashed line at t=1097 marks where the survival call replayed — the visual proof of the retry. Censored at the session end so the post-session tail doesn't stretch the axis. |
| `scatter()` | Generic feature-vs-outcome scatter with participant-ID labels and a trend line — used for the lesson1→post-score and nav→confusion figures. Participant IDs (not names) are annotated because the figures are committed. |
| `import numpy`/`os` mid-file | Placed just before first use — the file grew organically; functionally fine, stylistically imperfect. |

## make_pca.py — unsupervised behavior profiles

| Construct | Why |
|---|---|
| `FEATS` | A curated 10-feature subset (timing + stillness + head-pose + motion contrast) — deliberately excludes redundant/quasi-constant columns so PCs reflect behavior, not noise. |
| `StandardScaler` + `PCA(n_components=2)` | Features are on wildly different scales (seconds vs. ratios); standardizing is required before PCA or `session_s` would dominate PC1 purely by magnitude. |
| `df.iterrows()` annotation | Each point is labeled with its participant ID — the direct index `i` is required because `Z` rows align with `df`'s positional order after `reset_index`. |
| two figures (engagement / confusion) | Same embedding, two colorings — shows whether the behavior-space structure aligns with either label. PC1 ≈ 48 % of variance, PC2 ≈ 21 %. |

## make_pdf.py — README -> PDF

| Construct | Why |
|---|---|
| `Doc(FPDF)` + `footer()` | fpdf2 is pure Python — no LaTeX/wkhtmltopdf dependency on Windows. Footer adds a page label to every page automatically. |
| `clean()` | Strips markdown (`**`, backticks) and replaces Unicode the built-in Helvetica can't encode (`→`, `≈`, `ρ`, smart quotes) with ASCII — without this, fpdf2 raises or prints `?`. Latin-1 encoding with `replace` is the final safety net. |
| `render_table()` | Column widths are computed from actual string widths then scaled to fit `CW` — markdown tables have no width info, so this auto-fits them. Header row gets bold + fill. |
| the `while` loop dispatch | One pass over README lines handling each markdown element (headings, tables, images, bullets, blockquotes, code blocks) — the README uses a limited subset, so a line-based renderer is sufficient and avoids a markdown dependency. |
| image handling | `pdf.image(..., w=CW-20)` embeds the committed PNG figures inline — this is what puts the three findings figures in the PDF. |

---

## verify.py / verify_transcripts.py — independent audits

| Construct | Why |
|---|---|
| `RESULTS` + `record()`/`expect()` | Every check appends `(name, ok, detail)` so the final report lists exactly what was verified and how — an audit trail, not just a boolean. |
| `load_inputs()` | Loads all five committed CSVs once; a missing file records a failure instead of crashing — verification must report, not abort. |
| per-anomaly check functions (`check_p02_retry`, `check_p04_gap`, `check_p07_notranscript`, `check_p15_restart`, `check_p05_single_attempt`) | Each exists because it caught a real bug during development (P05/P06 split artifact, P04 NaN-vs-zero, P07 truncation, P15 restart, P02 genuine retry). They are regression guards. |
| `check_nan_convention()` | Enforces the project's core rule: unobserved phases are NaN, never 0 — the single most important data-integrity invariant. |
| `recompute_rho()`/`csv_rho()`/`check_all_correlations_reproduce()` | Independently recomputes every Spearman ρ rather than trusting the committed CSV — catches stale or hand-edited outputs. 324 rows, 0 mismatches. |
| `check_pii_hygiene()` | Runs `git ls-files` and fails if any name/email/raw-media file is tracked — automated enforcement of the privacy rule. |
| `verify_transcripts.py` functions | Audits the raw .vtt/.mp4 inputs verify.py cannot see: shared-audio cue presence, landmark hints, duration bounds, phase play-order, survival-call coverage. Caught the `*.vtt`/`*.transcript.vtt` glob double-count during its own development. |
| `print_report()` + `SystemExit` | Non-zero exit on any failure so the checks can gate re-runs in scripts or CI. |

## Cross-cutting decisions worth remembering

- **Missing ≠ zero.** P04 (late transcript) and P07 (no transcript/truncated
  video) produce NaN features, never 0 — "unobserved" must not masquerade as
  "didn't happen."
- **Names stay local.** `participants.csv` and survey exports contain PII and
  are `.gitignore`d; every committed artifact uses `participant_id` (P01–P20).
- **Caches are versioned by content.** `*_framesig.csv` recomputes when the
  `cam_motion` column is absent; `*_face.csv`/`*_blend.csv` are skipped
  independently — re-running a stage never redoes finished work.
- **Session window everywhere.** Every behavioral feature is restricted to
  `[s0, s1]` (first app frame → sustained desktop/interview) so survey-filling
  and interview time can't contaminate "in-app behavior."
- **Honest nulls are results.** The LASSO/LOO models report R²<0 and
  majority-baseline accuracy — that null is a finding about n=19 +
  session-level labels, documented rather than hidden.
- **Verify before trusting.** The P05/P06 retry artifact and the P02 real
  retry were both caught by checking transcripts against features — any
  surprising correlation gets a sanity check before it enters the report.

*Last updated: after the facial-blendshape pass and PCA figures.*
*Blendshape batch status at time of writing: in progress (per-second
action-unit extraction via MediaPipe FaceLandmarker).*
