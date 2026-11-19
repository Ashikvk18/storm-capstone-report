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


