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


