"""Step 7: interpretable models for RQ2.

n=20 -> keep it honest: standardized LASSO with leave-one-out CV for the
continuous outcomes, L1 logistic for the binary confusion flag.
Reports:
  - LOO R^2 / accuracy vs a predict-the-mean/majority baseline
  - feature selection frequency across folds (stability)
  - median standardized coefficients (effect direction + size)
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Lasso, LogisticRegression
from sklearn.metrics import accuracy_score, r2_score
from sklearn.preprocessing import StandardScaler

# drop frame_motion_mean (composite proxy), flag cols, and the
# single-positive indicators (was_restarted) - nothing to learn from 1/20
FEATURES = [
    "session_s", "pre_app_s", "lesson1_s", "quiz1_s", "lesson2_s",
    "survival_call_s", "survival_nav_s", "final_quiz_s",
    "survival_attempts", "speech_in_session_s",
    "quiz1_correct", "finalq_correct", "finalq_wrong",
    "webcam_motion_mean", "webcam_still_ratio", "webcam_longest_still_s",
    "cam_motion_lessons", "cam_motion_survival_nav",
    "face_detect_ratio", "head_yaw_std", "head_pitch_std",
    "head_turn_rate", "pitch_mean", "look_away_ratio",
    "expr_smile_mean", "expr_smile_max", "expr_frown_mean",
    "expr_brow_up_mean", "expr_brow_up_max", "expr_blink_mean",
    "expr_jaw_mean", "expr_sneer_mean", "expr_stretch_mean",
]
ALPHAS = np.logspace(-2, 1.5, 40)


def lasso_loo(X, y):
    """LOO predictions + per-fold selection stats for LASSO."""
    n = len(y)
    preds = np.zeros(n)
    selected = np.zeros(X.shape[1])
    coefs = np.zeros((n, X.shape[1]))
    for i in range(n):
        m = np.ones(n, bool)
        m[i] = False
        # inner 5-fold CV to pick alpha on the training fold
        best_a, best_mse = ALPHAS[0], np.inf
        idx = np.where(m)[0]
        for a in ALPHAS:
            errs = []
            for k in range(5):
                te = idx[k::5]
                tr = np.setdiff1d(idx, te)
                if len(tr) < 3:
                    continue
                lr = Lasso(alpha=a, max_iter=10000).fit(X[tr], y[tr])
                errs.append(((lr.predict(X[te]) - y[te]) ** 2).mean())
            mse = np.mean(errs) if errs else np.inf
            if mse < best_mse:
                best_mse, best_a = mse, a
        lr = Lasso(alpha=best_a, max_iter=10000).fit(X[m], y[m])
        preds[i] = lr.predict(X[i:i + 1])[0]
        selected += lr.coef_ != 0
        coefs[i] = lr.coef_
    return preds, selected, coefs


def report_regression(name, X, y, fnames):
    preds, selected, coefs = lasso_loo(X, y)
    r2 = r2_score(y, preds)
    base_r2 = r2_score(y, np.full_like(y, y.mean()))
    mae = np.abs(preds - y).mean()
    print(f"\n=== {name} (n={len(y)}) ===")
    print(f"LOO R^2 = {r2:.3f}   MAE = {mae:.3f}   "
          f"(mean-baseline R^2 = {base_r2:.3f})")
    order = np.argsort(-selected)
    print(f"feature                 selected/{len(y)}  median_coef")
    for j in order:
        if selected[j] == 0:
            continue
        print(f"  {fnames[j]:24s} {int(selected[j]):4d}      "
              f"{np.median(coefs[:, j]):+.3f}")


def report_binary(name, X, y, fnames):
    n = len(y)
    preds = np.zeros(n)
    coefs = np.zeros((n, X.shape[1]))
    for i in range(n):
        m = np.ones(n, bool)
        m[i] = False
        lr = LogisticRegression(penalty="l1", solver="liblinear", C=0.5,
                                max_iter=5000).fit(X[m], y[m])
        preds[i] = lr.predict(X[i:i + 1])[0]
        coefs[i] = lr.coef_[0]
    acc = accuracy_score(y, preds)
    maj = accuracy_score(y, np.full(n, np.bincount(y.astype(int)).argmax()))
    print(f"\n=== {name} (n={n}) ===")
    print(f"LOO accuracy = {acc:.2f}   majority baseline = {maj:.2f}")
    nz = np.abs(coefs).sum(0) > 0
    for j in np.argsort(-np.abs(coefs).mean(0)):
        if not nz[j]:
            continue
        print(f"  {fnames[j]:24s} mean_coef {np.mean(coefs[:, j]):+.3f}")


def main():
    feat = pd.read_csv("data/features.csv")
    lab = pd.read_csv("data/labels.csv")
    df = feat.merge(lab, on="participant_id", how="inner")
    df = df[df["engagement"].notna()].reset_index(drop=True)
    df["confusion_any"] = (df["confusion"] > 0).astype(int)

    X_df = df[FEATURES]
    # median-impute the few NaNs (P07 transcript-less row)
    X = StandardScaler().fit_transform(X_df.fillna(X_df.median()))

    rows = []
    for tgt in ("engagement", "confusion"):
        y = df[tgt].to_numpy(float)
        report_regression(tgt, X, y, FEATURES)
        preds, selected, coefs = lasso_loo(X, y)
        for j, f in enumerate(FEATURES):
            rows.append({"target": tgt, "feature": f,
                         "selected_folds": int(selected[j]),
                         "median_coef": round(np.median(coefs[:, j]), 3)})
    report_binary("confusion_any", X,
                  df["confusion_any"].to_numpy(int), FEATURES)
    pd.DataFrame(rows).to_csv("data/model_coefficients.csv", index=False)
    print("\nwrote data/model_coefficients.csv")


if __name__ == "__main__":
    main()
