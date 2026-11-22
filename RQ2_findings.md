# RQ2 Findings — Explainable Behavioral Features of Engagement and Confusion

*Draft analysis summary for the capstone report. All data de-identified (PIDs only).*

## 1. Data

- **20 Zoom screen recordings** of Storm VR sessions (Jan–Apr 2026), recovered
  from a damaged ZIP archive via stream-level extraction.
- Each recording: fullscreen Unity app + webcam overlay (top-right) +
  Zoom auto-transcript (.vtt) of app narration and post-session interviews.
- **No in-app telemetry exists.** All behavioral measures are video-derived.
- **20 participants** usable for labeled analysis (P07's recording is
  truncated mid-session with no transcript).

## 2. Pipeline

`extract_zip.py` (archive recovery) → `segment_sessions.py` (phase
segmentation) → `extract_features.py` (behavioral features) →
`build_labels.py` (survey composites) → `explore.py` / `model_rq2.py`
(analysis).

All committed outputs are independently re-checked by
`verify.py` / `verify_transcripts.py` (114 checks total; see
`VERIFICATION.md`).

**Segmentation** fuses two signals: VTT narration cues (phase landmarks like
"welcome to the tornado formation lesson") and 1-fps frame signatures
(sustained white-desktop detection for session end). Phases:
pre_app → lesson1 → quiz1 → lesson2 → impacts → survival_call →
survival_nav → final_quiz → post_app → interview.

**Robustness cases handled:** app restart mid-recording (P15, prior run
labeled `aborted`), untranscribed head (P04, phases censored to NaN),
truncated/transcript-less recording (P07), scenario replay (P02).

## 3. Features (all explainable)

Timing (session + per-phase dwell), survival attempts/retries, quiz
correct/incorrect counts from verbalized feedback, participant speech
seconds, webcam motion energy / stillness ratio / longest still streak,
cam-motion contrast (lessons vs navigation), plus data-quality flags.

**ML-derived head-pose features** (`extract_face.py`): MediaPipe
FaceLandmarker runs on the webcam overlay at 1 fps, estimating head
yaw/pitch/roll, face presence and position. Aggregated per session:
face detection ratio, yaw/pitch spread, head-turn rate, pitch bias, and
look-away ratio (pose deviating >20–25° from each participant's own
median — controls for camera mounting; P05 sits at −25° pitch and P09's
overlay was off during the app, so raw thresholds would mislead).

**Facial expression dynamics** (same model, `*_blend.csv`): 16 facial
action units per second (brow raise, eye blink, jaw drop, smile, frown,
mouth stretch/pucker, nose sneer, cheek puff), aggregated per session
into 9 interpretable features (mean/max smile, mean frown, mean brow-up,
blink rate, jaw openness). Faces are ~90 px so these are noisy proxies,
not emotion labels.

## 4. Results

### 4a. Descriptive associations (Spearman, n≈17–19)

| Feature → Outcome | ρ | p | Interpretation |
|---|---|---|---|
| lesson1_s → post_score | +0.51 | .039 | **Strongest finding.** Lesson-1 time is bimodal (~68s vs ~130s): the extra ~70s is dwell on "Next →" interstitial screens. Deliberate pacing → higher knowledge score. |
| finalq_wrong → post_score | −0.48 | .042 | Internal validity check: wrong answers → lower score. |
| session_s → GUESS full | +0.49 | .033 | Longer app time → higher reported engagement. |
| session_s → perceived_learning | +0.48 | .040 | Same direction. |
| webcam_longest_still_s → complexity | −0.54 | .017 | Longer stillness → lower perceived complexity (focused vs lost — ambiguous). |
| **look_away_ratio → effort** | **−0.64** | **.005** | **Strongest single association.** Participants whose head pose deviated from their own median more often reported less effort — a visible-disengagement signal. |
| look_away_ratio → engagement | −0.46 | .055 | Same direction: looking away → lower reported engagement. |
| head_pitch_std → effort | −0.53 | .020 | Less nod-pitch variability → higher effort ratings. |
| head_turn_rate → GUESS | +0.41 | .086 | More head scanning → higher game-experience scores. |
| expr_frown_mean → confusion | +0.57 | .013 | Frowning action units co-occur with reported confusion — direction matches the construct. |
| expr_stretch_mean → confusion | +0.54 | .020 | Mouth-stretch (grimace-like) activation, same direction. |
| **expr_brow_up_max → complexity** | **−.76** | **.0002** | **Largest |rho| in the dataset** — but fragile: a max-statistic over 1-fps blendshapes is sensitive to single-frame artifacts, the direction is counterintuitive, and it does not survive as a predictor. Hypothesis only. |
| expr_jaw_mean → learning_gain | −.48 | .045 | Jaw-drop activation vs knowledge gain — weak, exploratory. |
| survival_nav_s → confusion | +0.35 | .15 | Direction matches interviews but weak at this n. |

### 4b. Predictive modeling (LASSO, leave-one-out CV)

- Engagement: LOO R² = −0.21; Confusion: R² = −0.13 — **worse than
  predicting the mean.** Binary confusion: 0.63 acc < 0.74 majority
  baseline (with head-pose features included).
- **Honest null:** at n=19 with session-level labels and floor-compressed
  scales, these features do not support multivariate prediction. This is a
  legitimate methods finding: argues for per-phase labels and larger
  samples in future work.

### 4c. Qualitative triangulation — the real RQ2 story

The phase with the largest behavioral variance is **survival_nav**
(70–633s; all other scripted phases are near-constant). Post-session
interview transcripts show participants verbalizing exactly this:

| PID | nav_s | Interview evidence |
|---|---|---|
| P02 | 633 | "kind of hard to play"; call replayed after ~8.5 min failed nav |
| P04 | 308 | "at first I didn't know I was playing the game, I was just staring" |
| P13 | 215 | pace/navigation complaints |
| P8  | 145 | "the instructions were a little bit unclear" (re: navigation) |
| P10 | 128 | "the navigation was a little confusing… left and right" |
| P12 | 122 | "I don't really play much games, a little confused on the navigation" |
| P9  | 104 | "the controls being difficult and clunky made it harder to use" |
| P03 | 81  | "couldn't move for the first 2 minutes" |

**Navigation/controls difficulty is the dominant friction theme**, and it
lives in exactly the phase the timing data flags as most variable —
convergent quantitative + qualitative evidence for RQ2.

### Case study: P02 (see figures/p02_timeline.png)

Completed all lessons normally → entered survival scenario → failed to
reach the basement for ~8.5 min → scenario auto-restarted the phone call
→ completed on second attempt → reported elevated confusion. The replay
is visible verbatim in the transcript (mom-call dialogue replays at t=1097).

## 5. Limitations

- n≈19 usable sessions; survey labels are **session-level**, not per-lesson
- Confusion scale has floor effect (6/19 zeros → binary target used too)
- No eye tracking, gaze, or headset telemetry; head pose and webcam
  motion are coarse proxies (camera mounting/overlay visibility vary by
  machine; P09's self-view was off during the app → look_away NaN)
- Two lesson-1 durations are participant pacing on interstitials, not
  different builds (same narration, same-day counterexample P12/P13)
- P02's retry may partly reflect unfamiliarity with the controls
  ("I don't usually use a Dell"), not only content confusion
- Facial blendshapes are estimated from ~90 px webcam faces at 1 fps;
  max-statistic features (expr_*_max) can be driven by single-frame
  artifacts, and mean activations sit near the noise floor for some
  participants (P04's expressions are near-zero throughout)
- Multiple-testing: ~20 features × several outcomes; correlations are
  hypothesis-generating

## 6. Claims supported for the report

1. Video-derived phase timing is a feasible behavioral-data source when
   in-app logging is absent; scripted narration + frame signatures give
   reliable segmentation.
2. Dwell time on lesson-1 transitions predicts post-test knowledge
   (ρ≈0.5) — engagement-with-content, not just time.
3. Survival navigation time is the highest-variance behavior and the
   phase participants most often describe as confusing — a candidate
   confusion indicator for future instrumented studies.
4. Head-pose-derived attention features (look-away ratio, head-turn
   rate) correlate with engagement/effort scales in the expected
   direction (ρ ≈ −0.5 to −0.65) — the strongest behavioral signal in
   the dataset after lesson-1 dwell.
5. Facial action-unit dynamics (frown, mouth-stretch) correlate
   with reported confusion in the expected direction (rho ~ 0.55) —
   preliminary evidence that expression proxies carry signal, pending
   replication at larger n.
6. Session-level self-reports at n≈20 cannot support predictive modeling;
   per-phase experience sampling is needed.
