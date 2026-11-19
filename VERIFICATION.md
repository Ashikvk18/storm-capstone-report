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
