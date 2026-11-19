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


def load_phases():
    """Per-second phase labels, trimmed to the app window."""
    tl = pd.read_csv(TIMELINE_CSV)
    keep = tl["phase"].isin(PHASE_COLORS)
    return tl.loc[keep, ["t_sec", "phase"]]


def smooth(expr):
    """Rolling mean over SMOOTH_WINDOW seconds.

    Raw 1-fps blendshape scores flicker frame to frame; smoothing
    surfaces sustained expression (e.g., a frown held through a
    navigation struggle) instead of detection noise.
    """
    return expr[list(SERIES)].rolling(
        SMOOTH_WINDOW, center=True, min_periods=1).mean()


def phase_spans(ph):
    """Contiguous (phase, start, end) runs for background bands."""
    spans = []
    start = ph["t_sec"].iloc[0]
    cur = ph["phase"].iloc[0]
    for _, r in ph.iloc[1:].iterrows():
        if r["phase"] != cur:
            spans.append((cur, start, r["t_sec"]))
            cur, start = r["phase"], r["t_sec"]
    spans.append((cur, start, ph["t_sec"].iloc[-1] + 1))
    return spans


def plot(expr, ph):
    """Expression traces over phase bands + replay marker."""
    fig, ax = plt.subplots(figsize=(11, 3.4))
    sm = smooth(expr)
    t = expr["t_sec"].to_numpy()

    # phase bands first so traces draw on top
    for ph_name, a, b in phase_spans(ph):
        ax.axvspan(a, b, color=PHASE_COLORS[ph_name], alpha=0.12,
                   lw=0)

    colors = {"frown": "#8e3b46", "brow_raise": "#b5651d",
              "smile": "#3fa66a", "jaw_open": "#4c6fb3"}
    for name in SERIES:
        ax.plot(t, sm[name], label=name, color=colors[name], lw=1.4)

    ax.axvline(REPLAY_T, color="k", ls="--", lw=1)
    ax.annotate("call replays\n(scenario retry)", (REPLAY_T + 8, 0.92),
                fontsize=8, va="top")
    ax.annotate("~8.5 min failed navigation", (830, 0.92),
                ha="center", fontsize=8, color="#c94f4f")

    ax.set_xlim(t.min(), t.max())
    ax.set_ylim(0, 1)
    ax.set_xlabel("seconds into recording")
    ax.set_ylabel("action-unit activation (15s avg)")
    ax.set_title("P02 facial expressions across session phases")
    ax.legend(ncol=4, fontsize=8, loc="lower left", frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)
    print(f"wrote {OUT_PNG}")


