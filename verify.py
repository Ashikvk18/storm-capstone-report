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


