"""Generate report figures (de-identified, safe to commit).

  figures/p02_timeline.png   - P02 session phases incl. the failed
                               8.5-min navigation and scenario replay
  figures/nav_vs_confusion.png - survival_nav_s vs reported confusion
  figures/lesson1_vs_post.png  - lesson1 dwell vs post-test score
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import spearmanr

PHASE_ORDER = ["pre_app", "lesson1", "quiz1", "lesson2", "impacts",
               "survival_call", "survival_nav", "final_quiz", "post_app"]
COLORS = {"pre_app": "#bbbbbb", "lesson1": "#4c9be0", "quiz1": "#f2c14e",
          "lesson2": "#3fa66a", "impacts": "#8e6cc9",
          "survival_call": "#e07b54", "survival_nav": "#c94f4f",
          "final_quiz": "#f2c14e", "post_app": "#bbbbbb",
          "aborted": "#333333", "participant_speech": "#77d4d4",
          "app_idle": "#dddddd"}


def fig_p02():
    tl = pd.read_csv(
        "out/2026-01-20_StorM_P02_Kamsi Amaeshi_timeline.csv")
    fig, ax = plt.subplots(figsize=(11, 2.2))
    t = tl["t_sec"].to_numpy()
    for ph, grp in tl.groupby("phase"):
        pass  # draw contiguous runs instead
    run_start = 0
    for i in range(1, len(tl) + 1):
        if i == len(tl) or tl["phase"][i] != tl["phase"][run_start]:
            ph = tl["phase"][run_start]
            if ph in ("desktop", "interview"):
                run_start = i
                continue
            ax.barh(0, i - run_start, left=run_start, height=0.9,
                    color=COLORS.get(ph, "#999999"), edgecolor="white",
                    linewidth=0.3)
            run_start = i
    ax.axvline(1097, color="k", ls="--", lw=1)
    ax.annotate("call replays\n(scenario retry)", (1100, 0.52),
                ha="left", fontsize=8)
    ax.annotate("~8.5 min failed navigation", (820, 0.52),
                ha="center", fontsize=8, color="white")
    ax.set_xlim(0, 1340)
    ax.set_ylim(-0.7, 1.0)
    ax.set_yticks([])
    ax.set_xlabel("seconds into recording")
    ax.set_title("P02 session timeline (app window only)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[p])
               for p in PHASE_ORDER]
    ax.legend(handles, PHASE_ORDER, ncol=5, fontsize=7,
              loc="upper center", bbox_to_anchor=(0.5, -0.25),
              frameon=False)
    fig.tight_layout()
    fig.savefig("figures/p02_timeline.png", dpi=160,
                bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def scatter(xcol, ycol, fname, title, xlabel, ylabel):
    df = pd.read_csv("data/features.csv").merge(
        pd.read_csv("data/labels.csv"), on="participant_id")
    df = df.dropna(subset=[xcol, ycol])
    rho, p = spearmanr(df[xcol], df[ycol])
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(df[xcol], df[ycol], s=40, zorder=3)
    for _, r in df.iterrows():
        ax.annotate(r["participant_id"], (r[xcol], r[ycol]),
                    fontsize=6, xytext=(3, 3), textcoords="offset points")
    cf = np.polyfit(df[xcol], df[ycol], 1)
    xs = np.linspace(df[xcol].min(), df[xcol].max(), 50)
    ax.plot(xs, np.polyval(cf, xs), "r--", lw=1)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(f"{title} (rho={rho:.2f}, p={p:.3f})")
    fig.tight_layout()
    fig.savefig(f"figures/{fname}", dpi=160,
                bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


import numpy as np
import os

os.makedirs("figures", exist_ok=True)
fig_p02()
scatter("lesson1_s", "post_score", "lesson1_vs_post.png",
        "Lesson-1 dwell vs post-test score",
        "seconds in lesson 1", "post-test score (0-10)")
scatter("survival_nav_s", "confusion", "nav_vs_confusion.png",
        "Survival navigation time vs reported confusion",
        "seconds navigating to shelter", "confusion composite (0-10)")
print("wrote figures/")
