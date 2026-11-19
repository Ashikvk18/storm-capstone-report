"""P02 expression timeline: facial action units aligned to session phases.

Case-study figure for RQ2: does P02's face show confusion-related
expressions (frown, brow-raise, jaw-drop) during the ~8.5 min failed
survival navigation and the scenario replay?

Reads the per-second blendshape CSV (extract_face.py) and the phase
timeline (segment_sessions.py), smooths each action unit, and plots
them over a phase-band background.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

STEM = "2026-01-20_StorM_P02_Kamsi Amaeshi"
BLEND_CSV = f"out/{STEM}_blend.csv"
TIMELINE_CSV = f"out/{STEM}_timeline.csv"
OUT_PNG = "figures/p02_expressions.png"

# action units to plot: name -> blendshape columns to average.
# symmetric pairs are mean-combined; jawOpen stands alone.
# chosen for interpretability: frown/brow = confusion-adjacent,
# smile = positive affect, jaw = surprise/speech proxy
SERIES = {
    "frown": ("mouthFrownLeft", "mouthFrownRight"),
    "brow_raise": ("browInnerUp", "browOuterUpLeft",
                   "browOuterUpRight"),
    "smile": ("mouthSmileLeft", "mouthSmileRight"),
    "jaw_open": ("jawOpen",),
}

# phase bands drawn behind the traces; only app-window phases
PHASE_COLORS = {
    "lesson1": "#4c9be0", "quiz1": "#f2c14e", "lesson2": "#3fa66a",
    "impacts": "#8e6cc9", "survival_call": "#e07b54",
    "survival_nav": "#c94f4f", "final_quiz": "#f2c14e",
}

SMOOTH_WINDOW = 15  # seconds; blendshapes at 1fps are noisy, so a
                    # 15-s rolling mean shows sustained expression
                    # rather than single-frame artifacts
REPLAY_T = 1097     # second where P02's survival call replayed

def load_expressions():
    """Per-second action-unit series for P02.

    Symmetric blendshape pairs (Left/Right) are averaged so each
    SERIES entry becomes one column. Face-miss seconds keep NaN -
    they are unknown, not zero-expression.
    """
    bf = pd.read_csv(BLEND_CSV)
    expr = pd.DataFrame({"t_sec": bf["t_sec"]})
    for name, cols in SERIES.items():
        expr[name] = bf[list(cols)].mean(axis=1)
    expr.loc[bf["face_found"] != 1, list(SERIES)] = np.nan
    return expr


