# Data Dictionary — committed CSVs

Column-by-column definitions for every de-identified dataset in `data/`.
Conventions used throughout:

- **`participant_id` (P01–P22)** — the only identifier ever committed;
  real names live only in gitignored `participants.csv`.
- **NaN ≠ 0** — a missing value means "unobserved" (truncated video,
  late transcript, face not detected), never "didn't happen."
- All durations are **seconds**; all timestamps are **seconds into the
  recording**.
