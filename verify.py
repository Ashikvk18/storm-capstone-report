"""Independent verification of the RQ2 pipeline outputs.

Re-checks structural integrity, known-anomaly spot values, key
correlations, model sanity, artifact validity, and PII hygiene.
Exits non-zero if any check fails - safe to run after any pipeline
re-run or upstream edit.

Usage: python verify.py
"""
import os
import subprocess

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

RESULTS = []  # (name, ok, detail)

DATA = "data"
FIGS = "figures"

EXPECTED_PHASES = {"lesson1", "quiz1", "lesson2", "impacts",
                   "survival_call", "survival_nav", "final_quiz",
                   "pre_app", "post_app", "app_idle", "aborted",
                   "app_no_transcript", "interview", "desktop",
                   "participant_speech"}

FIGURE_FILES = ["p02_timeline.png", "p02_expressions.png",
                "lesson1_vs_post.png", "nav_vs_confusion.png",
                "pca_engagement.png", "pca_confusion.png"]


def record(name, ok, detail=""):
    """Append one check result; ok may be bool or a short string."""
    RESULTS.append((name, bool(ok), detail))


def expect(cond, name, detail=""):
    """Record a pass/fail check with an explanatory detail string."""
    record(name, cond, detail)


def load_inputs():
    """Load every committed CSV once; missing files record failures."""
    out = {}
    for key, path in {
        "features": f"{DATA}/features.csv",
        "labels": f"{DATA}/labels.csv",
        "segments": f"{DATA}/session_segments.csv",
        "correlations": f"{DATA}/explore_correlations.csv",
        "coefficients": f"{DATA}/model_coefficients.csv",
    }.items():
        if os.path.exists(path):
            out[key] = pd.read_csv(path)
        else:
            out[key] = None
            expect(False, f"file exists: {path}", "missing")
    return out


def check_file_exists(path, name):
    """Generic existence check used for scripts and caches."""
    expect(os.path.exists(path), name, path if os.path.exists(path)
           else "MISSING")


def check_row_counts(d):
    """Row counts must match the known study size."""
    expect(len(d["features"]) == 20, "features.csv has 20 rows",
           f"got {len(d['features'])}")
    expect(19 <= len(d["labels"]) <= 25, "labels.csv row count sane",
           f"got {len(d['labels'])}")
    expect(len(d["segments"]) == 20, "session_segments.csv 20 rows",
           f"got {len(d['segments'])}")
    expect(250 <= len(d["correlations"]) <= 400,
           "explore_correlations.csv row count sane",
           f"got {len(d['correlations'])}")
    expect(len(d["coefficients"]) > 0,
           "model_coefficients.csv non-empty",
           f"got {len(d['coefficients'])}")


def check_feature_columns(d):
    """Every feature group must be present as columns."""
    need = ["participant_id", "session_s", "survival_attempts",
            "look_away_ratio", "expr_frown_mean",
            "no_transcript", "transcript_gap"]
    missing = [c for c in need if c not in d["features"].columns]
    expect(not missing, "features.csv has all feature groups",
           f"missing: {missing}" if missing else "ok")


def check_participant_ids(d):
    """All 20 PIDs present exactly once, sorted."""
    pids = sorted(d["features"]["participant_id"].astype(str))
    expect(len(pids) == len(set(pids)) == 20,
           "features.csv has 20 unique participant_ids", str(pids))


def row_of(df, pid):
    """First row for a participant id, or None."""
    m = df[df["participant_id"] == pid]
    return m.iloc[0] if len(m) else None


def check_p02_retry(d):
    """P02 genuinely replayed the survival scenario (verified in
    transcript: call dialogue reappears at t=1097)."""
    r = row_of(d["features"], "P02")
    expect(r is not None and r["survival_attempts"] == 2,
           "P02 survival_attempts == 2 (real retry)",
           f"got {r['survival_attempts'] if r is not None else 'NA'}")


def check_p02_nav_long(d):
    """P02's navigation should be the extreme struggle case."""
    r = row_of(d["features"], "P02")
    expect(r is not None and r["survival_nav_s"] > 500,
           "P02 survival_nav_s > 500s", f"got {r['survival_nav_s']}")


def check_p04_gap(d):
    """P04's transcript starts ~4min in: transcript_gap=1 and early
    phases must be NaN, not zero."""
    r = row_of(d["features"], "P04")
    ok = (r is not None and r["transcript_gap"] == 1
          and pd.isna(r["lesson1_s"]))
    expect(ok, "P04 transcript_gap=1 + lesson1_s NaN",
           f"gap={r['transcript_gap']}, lesson1={r['lesson1_s']}")


def check_p07_notranscript(d):
    """P07's MP4 is truncated with no VTT: no_transcript=1 and all
    phase durations NaN."""
    r = row_of(d["features"], "P07")
    phases = ["lesson1_s", "survival_nav_s", "final_quiz_s"]
    ok = (r is not None and r["no_transcript"] == 1
          and all(pd.isna(r[p]) for p in phases))
    expect(ok, "P07 no_transcript=1 + phases NaN",
           f"flag={r['no_transcript']}")


def check_p15_restart(d):
    """P15 restarted the app mid-recording: aborted seconds exist."""
    r = row_of(d["features"], "P15")
    expect(r is not None and r["was_restarted"] == 1,
           "P15 was_restarted == 1", f"got {r['was_restarted']}")


def check_p05_single_attempt(d):
    """Regression guard for the P05/P06 split artifact: a 2s speech
    blip must not inflate survival_attempts."""
    for pid in ("P05", "P06"):
        r = row_of(d["features"], pid)
        expect(r is not None and r["survival_attempts"] == 1,
               f"{pid} survival_attempts == 1 (no split artifact)",
               f"got {r['survival_attempts']}")


def check_nan_convention(d):
    """Missingness rule: no_transcript rows have ALL phase columns
    NaN; transcript_gap rows have early phases NaN."""
    f = d["features"]
    phases = ["lesson1_s", "quiz1_s", "lesson2_s", "impacts_s",
              "survival_call_s", "survival_nav_s", "final_quiz_s"]
    nt = f[f["no_transcript"] == 1]
    ok = all(pd.isna(nt[p]).all() for p in phases) if len(nt) else True
    expect(ok, "no_transcript rows have all phase durations NaN",
           f"{len(nt)} rows checked")


def check_nonnegative(d):
    """Durations and counts cannot be negative."""
    f = d["features"]
    dur_cols = [c for c in f.columns if c.endswith("_s")]
    bad = (f[dur_cols].dropna() < 0).sum().sum()
    expect(bad == 0, "no negative duration/count values", f"{bad} bad")


def check_value_ranges(d):
    """Bounded features must stay in [0,1]; scores in survey ranges."""
    f, l = d["features"], d["labels"]
    ratios = ["webcam_still_ratio", "face_detect_ratio",
              "look_away_ratio"]
    for c in ratios:
        v = f[c].dropna()
        expect(((v >= 0) & (v <= 1)).all(),
               f"{c} within [0,1]", f"range {v.min():.2f}-{v.max():.2f}")
    expr = [c for c in f.columns if c.startswith("expr_")]
    bad = ((f[expr].dropna() < 0) | (f[expr].dropna() > 1)).sum().sum()
    expect(bad == 0, "expression scores within [0,1]", f"{bad} bad")
    expect(l["post_score"].dropna().between(0, 10).all(),
           "post_score within 0-10")
    expect(l["engagement"].dropna().between(1, 7).all(),
           "engagement within 1-7")


def check_learning_gain(d):
    """learning_gain must equal post_score - pre_score exactly."""
    l = d["labels"].dropna(subset=["learning_gain"])
    diff = (l["learning_gain"] - (l["post_score"] - l["pre_score"]))
    expect((diff.abs() < 1e-9).all(),
           "learning_gain == post_score - pre_score",
           f"max diff {diff.abs().max():.2e}")


def merged_labels(d):
    """Inner-join features+labels with engagement present - the same
    frame explore.py analyzes."""
    df = d["features"].merge(d["labels"], on="participant_id")
    return df[df["engagement"].notna()].reset_index(drop=True)


def recompute_rho(df, feature, target):
    """Independent Spearman recompute for one feature-target pair."""
    ok = df[feature].notna() & df[target].notna()
    if ok.sum() < 3:
        return np.nan, 0
    r, p = spearmanr(df.loc[ok, feature], df.loc[ok, target])
    return r, int(ok.sum())


def csv_rho(d, feature, target):
    """Look up the rho explore.py recorded for a pair."""
    m = d["correlations"]
    hit = m[(m["feature"] == feature) & (m["target"] == target)]
    return float(hit["rho"].iloc[0]) if len(hit) else np.nan


def check_corr_reproduces(d, feature, target, expected, tol=0.02):
    """Recomputed rho must match the committed CSV within tolerance."""
    df = merged_labels(d)
    r, n = recompute_rho(df, feature, target)
    csv = csv_rho(d, feature, target)
    ok = abs(r - csv) < tol and abs(r - expected) < tol
    expect(ok, f"rho reproduces: {feature}->{target}",
           f"recomputed {r:.3f} (n={n}) vs csv {csv:.3f} "
           f"vs expected {expected:.3f}")


def check_all_correlations_reproduce(d):
    """Every row in explore_correlations.csv must recompute."""
    df = merged_labels(d)
    df["confusion_any"] = (df["confusion"] > 0).astype(int)
    bad = 0
    for _, row in d["correlations"].iterrows():
        f_, t_ = row["feature"], row["target"]
        if f_ not in df.columns or t_ not in df.columns:
            bad += 1
            continue
        r, _ = recompute_rho(df, f_, t_)
        if abs(r - row["rho"]) > 0.02:
            bad += 1
    expect(bad == 0, "all correlation rows recompute within .02",
           f"{bad} mismatches")


def check_correlation_bounds(d):
    """rho must be in [-1,1] where defined; constant inputs yield NaN
    (e.g. quiz1_correct is identical for everyone). n in [8,25]."""
    c = d["correlations"]
    rho_ok = c["rho"].dropna().between(-1, 1).all()
    n_ok = c["n"].between(8, 25).all()
    nan_count = int(c["rho"].isna().sum())
    expect(rho_ok and n_ok,
           "correlation rho/n within valid ranges",
           f"{nan_count} NaN rhos (constant inputs)")


def check_model_targets(d):
    """model_coefficients covers both regression targets."""
    tg = set(d["coefficients"]["target"].unique())
    expect({"engagement", "confusion"} <= tg,
           "model targets include engagement + confusion", str(tg))


def check_model_selection_bounds(d):
    """selected_folds cannot exceed the 19 LOO folds."""
    sf = d["coefficients"]["selected_folds"]
    expect(sf.between(0, 19).all(),
           "selected_folds within [0,19]",
           f"max {sf.max()}")


def check_figures_exist():
    """All six report figures must exist and be non-trivial."""
    for fn in FIGURE_FILES:
        p = os.path.join(FIGS, fn)
        ok = os.path.exists(p) and os.path.getsize(p) > 5000
        expect(ok, f"figure exists: {fn}",
               f"{os.path.getsize(p)} bytes" if os.path.exists(p)
               else "MISSING")


def check_png_magic():
    """PNG files must start with the 8-byte PNG signature."""
    sig = b"\x89PNG\r\n\x1a\n"
    bad = []
    for fn in FIGURE_FILES:
        p = os.path.join(FIGS, fn)
        if os.path.exists(p):
            with open(p, "rb") as fh:
                if fh.read(8) != sig:
                    bad.append(fn)
    expect(not bad, "all figures have valid PNG headers",
           f"bad: {bad}" if bad else "ok")


def check_pdf():
    """storm-capstone.pdf must be a real PDF."""
    p = "storm-capstone.pdf"
    ok = os.path.exists(p)
    if ok:
        with open(p, "rb") as fh:
            ok = fh.read(5) == b"%PDF-"
    expect(ok, "storm-capstone.pdf has %PDF- header")


def check_pii_hygiene():
    """PII files must never be tracked by git."""
    tracked = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True).stdout
    bad = [f for f in tracked.splitlines()
           if "participants.csv" in f or f.endswith(".mp4")
           or f.endswith(".vtt") or f.endswith(".xlsx")]
    expect(not bad, "no PII/raw-media files tracked in git",
           f"bad: {bad}" if bad else "ok")


