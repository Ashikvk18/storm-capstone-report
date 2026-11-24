"""Multi-session facial-expression figure for the report.

Small multiples: the same four action units (frown, brow-raise, smile,
jaw-open) over session time for six participants, with phase bands
behind the traces. Companion to make_expr_timeline.py (P02 case study).

Reads out/*_blend.csv (extract_face.py) and out/*_timeline.csv
(segment_sessions.py); 15-s rolling mean, same as the P02 figure.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# participant label -> recording stem in out/
PARTICIPANTS = [
    ("P02", "2026-01-20_StorM_P02_Kamsi Amaeshi"),
    ("P05", "2026-01-27_StorM_P05_Ezra_Thompson"),
    ("P08", "0217_P8"),
    ("P12", "0326_P12"),
    ("P14", "0327_P14"),
    ("P21", "0403_P21_Recording"),
]

SERIES = {
    "frown": ("mouthFrownLeft", "mouthFrownRight"),
    "brow_raise": ("browInnerUp", "browOuterUpLeft",
                   "browOuterUpRight"),
    "smile": ("mouthSmileLeft", "mouthSmileRight"),
    "jaw_open": ("jawOpen",),
}
COLORS = {"frown": "#8e3b46", "brow_raise": "#b5651d",
          "smile": "#3fa66a", "jaw_open": "#4c6fb3"}

PHASE_COLORS = {
    "lesson1": "#4c9be0", "quiz1": "#f2c14e", "lesson2": "#3fa66a",
    "impacts": "#8e6cc9", "survival_call": "#e07b54",
    "survival_nav": "#c94f4f", "final_quiz": "#f2c14e",
}
SMOOTH_WINDOW = 15


def load_expr(stem):
    bf = pd.read_csv(f"out/{stem}_blend.csv")
    expr = pd.DataFrame({"t_sec": bf["t_sec"]})
    for name, cols in SERIES.items():
        expr[name] = bf[list(cols)].mean(axis=1)
    expr.loc[bf["face_found"] != 1, list(SERIES)] = np.nan
    return expr


def load_phases(stem):
    tl = pd.read_csv(f"out/{stem}_timeline.csv")
    return tl.loc[tl["phase"].isin(PHASE_COLORS), ["t_sec", "phase"]]


def spans(ph):
    out, start, cur = [], ph["t_sec"].iloc[0], ph["phase"].iloc[0]
    for _, r in ph.iloc[1:].iterrows():
        if r["phase"] != cur:
            out.append((cur, start, r["t_sec"]))
            cur, start = r["phase"], r["t_sec"]
    out.append((cur, start, ph["t_sec"].iloc[-1] + 1))
    return out


def main():
    fig, axes = plt.subplots(2, 3, figsize=(14, 7), sharey=True)
    for ax, (pid, stem) in zip(axes.flat, PARTICIPANTS):
        expr = load_expr(stem)
        ph = load_phases(stem)
        t = expr["t_sec"].to_numpy()
        sm = expr[list(SERIES)].rolling(
            SMOOTH_WINDOW, center=True, min_periods=1).mean()
        for name, a, b in spans(ph):
            ax.axvspan(a, b, color=PHASE_COLORS[name], alpha=0.10, lw=0)
        for s in SERIES:
            ax.plot(t, sm[s], color=COLORS[s], lw=1.1)
        ax.set_title(pid, fontsize=11, loc="left")
        ax.set_xlim(t.min(), t.max())
        ax.set_ylim(0, 1)
        ax.tick_params(labelsize=7)
    for ax in axes[1]:
        ax.set_xlabel("seconds into recording", fontsize=8)
    for ax in axes[:, 0]:
        ax.set_ylabel("action-unit activation (15s avg)", fontsize=8)
    handles = [plt.Line2D([0], [0], color=COLORS[s], lw=1.4)
               for s in SERIES]
    fig.legend(handles, list(SERIES), ncol=4, fontsize=9,
               loc="upper center", frameon=False,
               bbox_to_anchor=(0.5, 1.02))
    fig.suptitle("Facial action-unit activation across sessions "
                 "(frown, brow-raise, smile, jaw-open)",
                 fontsize=12)
    fig.tight_layout()
    fig.savefig("figures/expr_across_sessions.png", dpi=160,
                bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print("wrote figures/expr_across_sessions.png")


if __name__ == "__main__":
    main()
