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
