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
