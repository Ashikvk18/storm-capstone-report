"""Step 6: join video features with survey labels -> first look at RQ2.

Merges data/features.csv with data/labels.csv and prints Spearman
correlations between each behavioral feature and the self-report
outcomes (engagement, confusion; learning scores for context).

n ~= 19, so this is hypothesis-generating only - no multiple-testing
correction, treat p-values as rough guides.
"""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

FEATURES = [
    "session_s", "pre_app_s", "lesson1_s", "quiz1_s", "lesson2_s",
    "impacts_s", "survival_call_s", "survival_nav_s", "final_quiz_s",
    "post_app_s", "survival_attempts", "speech_in_session_s",
    "quiz1_correct", "finalq_correct", "finalq_wrong",
    "webcam_motion_mean", "webcam_still_ratio", "webcam_longest_still_s",
    "cam_motion_lessons", "cam_motion_survival_nav", "frame_motion_mean",
]
TARGETS = ["engagement", "confusion", "post_score", "learning_gain"]


def main():
    feat = pd.read_csv("data/features.csv")
    lab = pd.read_csv("data/labels.csv")
    df = feat.merge(lab, on="participant_id", how="inner")
    df = df[df["engagement"].notna()]
    print(f"joined: {len(df)} participants with features + labels")
    print("(excluded: P17 no post-survey; P07 keeps row but phase "
          "features are NaN)\n")

    rows = []
    for tgt in TARGETS:
        for f in FEATURES:
            x, y = df[f], df[tgt]
            ok = x.notna() & y.notna()
            if ok.sum() < 8:
                continue
            rho, p = spearmanr(x[ok], y[ok])
            rows.append({"target": tgt, "feature": f,
                         "n": int(ok.sum()),
                         "rho": round(rho, 3), "p": round(p, 4)})
    res = pd.DataFrame(rows)
    res["abs"] = res["rho"].abs()

    for tgt in TARGETS:
        print(f"=== {tgt} ===")
        sub = res[res["target"] == tgt].sort_values("abs", ascending=False)
        print(sub.head(10)[["feature", "n", "rho", "p"]].to_string(
            index=False))
        print()

    res.drop(columns="abs").to_csv("data/explore_correlations.csv",
                                   index=False)
    print("wrote data/explore_correlations.csv")


if __name__ == "__main__":
    main()
