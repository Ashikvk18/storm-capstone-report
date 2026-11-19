# Verification Report — RQ2 Pipeline

`verify.py` independently re-checks every committed artifact: file
existence, row counts, schema, known-anomaly spot values, the
missingness conventions, every correlation in
`explore_correlations.csv`, model sanity, figure/PDF integrity, and
PII hygiene. It exits non-zero on any failure.

```bash
python verify.py    # prints PASS/FAIL per check; exit 1 on failure
```

Latest run: **52 checks, 52 passed** — see `verification_output.txt`.

## Check groups

| Group | What it proves |
|---|---|
| File existence | All pipeline scripts + `face_landmarker.task` present |
| Row counts | Study-size sanity (20 sessions, ~23 label rows, 324 correlations) |
| Schema | Required feature groups/columns present; 20 unique PIDs |
| Anomaly spot-checks | P02 retry, P04 gap, P07 truncation, P15 restart, P05/P06 no-split |
| Missingness | NaN (not 0) for unobserved phases; no negative values; bounded ranges |
| Correlations | All 324 rows recompute within ±.02 of committed CSV |
| Model | Both targets present; selection counts within 19 folds |
| Artifacts | 6 PNGs valid headers, PDF has `%PDF-` magic |
| PII | No names/emails/raw media tracked in git |

## File existence (8 checks)

All seven pipeline scripts (`extract_zip`, `segment_sessions`,
`extract_features`, `extract_face`, `build_labels`, `explore`,
`model_rq2`) plus the `face_landmarker.task` model file must exist —
missing inputs would silently produce empty outputs downstream.

## Row counts (5 checks)

- `features.csv` — exactly 20 rows (one per recording)
- `labels.csv` — 23 rows (19 labeled participants + survey-only rows)
- `session_segments.csv` — 20 rows
- `explore_correlations.csv` — 324 rows (36 features × 9 targets,
  minus pairs dropped for n<8)
- `model_coefficients.csv` — non-empty

## Schema checks (2 checks)

`features.csv` must contain columns from every feature group
(`session_s`, `survival_attempts`, `look_away_ratio`,
`expr_frown_mean`, `no_transcript`, `transcript_gap`), and all 20
participant IDs must be unique.

## Anomaly spot-checks — the cases that broke earlier versions

These checks exist because each one caught a real bug during
development:

- **P02 `survival_attempts` == 2** — the genuine replay (call dialogue
  recurs at t=1097 after ~8.5 min failed navigation)
- **P02 `survival_nav_s` > 500** — the extreme struggle case (633 s)
- **P04 `transcript_gap` == 1 + `lesson1_s` NaN** — transcript starts
  ~4 min in; unobserved ≠ zero
- **P07 `no_transcript` == 1 + phases NaN** — truncated MP4, no VTT
- **P15 `was_restarted` == 1** — app restarted mid-recording
- **P05/P06 `survival_attempts` == 1** — regression guard for the
  2-second-speech-blip split artifact

## Missingness and value-range checks (4 checks)

- `no_transcript` rows must have **all seven phase durations NaN**
- No negative durations or counts anywhere
- Ratio features (`webcam_still_ratio`, `face_detect_ratio`,
  `look_away_ratio`) within [0,1]
- All `expr_*` scores within [0,1]; `post_score` within 0–10;
  `engagement` within 1–7
- `learning_gain` == `post_score − pre_score` (max diff ~1e-16)

## Correlation reproduction (6 checks)

The four headline associations are recomputed independently and must
match both the committed CSV and the reported values:

| Feature → Target | Recomputed ρ | CSV ρ |
|---|---|---|
| look_away_ratio → effort | −.635 | −.635 |
| expr_frown_mean → confusion | +.573 | +.573 |
| lesson1_s → post_score | +.505 | +.505 |
| expr_brow_up_max → complexity | −.764 | −.764 |

Then **all 324 rows** of `explore_correlations.csv` are recomputed —
0 mismatches beyond ±.02. Bounds check: ρ ∈ [−1,1], n ∈ [8,25];
9 rows have NaN ρ because `quiz1_correct` is constant across
participants (a correlation is undefined on constant input — expected,
not an error).

## Model sanity (2 checks)

- `model_coefficients.csv` covers both regression targets
  (engagement, confusion)
- `selected_folds` ∈ [0,19] — cannot exceed the 19 leave-one-out folds
  (observed max: 6, i.e., no feature was stably selected — consistent
  with the reported null result)

## Artifact integrity (3 checks)

- All 6 figures exist and exceed 5 KB
- Every PNG starts with the 8-byte PNG signature
- `storm-capstone.pdf` starts with `%PDF-`

## PII and join hygiene (4 checks)

- `git ls-files` contains no `participants.csv`, `.mp4`, `.vtt`, or
  `.xlsx` — names/emails/raw media can never leak into the repo
- Every `features.csv` PID appears in `labels.csv` (all matched)
- `confusion_any` target exists in the correlation table and the
  positive rate (0.74) matches the known floor effect
- All `session_s` values positive (min 681 s)
- P02's timeline file contains only known phase labels
