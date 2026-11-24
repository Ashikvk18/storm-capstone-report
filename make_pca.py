"""PCA scatter of behavior profiles, colored by survey labels."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

FEATS = ["session_s", "lesson1_s", "survival_nav_s", "survival_attempts",
         "webcam_still_ratio", "webcam_longest_still_s",
         "head_turn_rate", "look_away_ratio",
         "cam_motion_lessons", "cam_motion_survival_nav"]


def main():
    df = pd.read_csv("data/features.csv").merge(
        pd.read_csv("data/labels.csv"), on="participant_id")
    df = df.dropna(subset=["engagement"]).reset_index(drop=True)
    X = StandardScaler().fit_transform(df[FEATS].fillna(df[FEATS].median()))
    pca = PCA(n_components=2).fit(X)
    Z = pca.transform(X)
    print("explained variance:", np.round(pca.explained_variance_ratio_, 3))

    for target, fname, title in [
            ("engagement", "pca_engagement.png",
             "PCA of behavior profiles, colored by engagement"),
            ("confusion", "pca_confusion.png",
             "PCA of behavior profiles, colored by confusion")]:
        fig, ax = plt.subplots(figsize=(6, 5))
        sc = ax.scatter(Z[:, 0], Z[:, 1], c=df[target], cmap="viridis",
                        s=45, edgecolors="k", linewidths=0.4)
        for i, r in df.iterrows():
            ax.annotate(r["participant_id"], (Z[i, 0], Z[i, 1]),
                        fontsize=6, xytext=(3, 3),
                        textcoords="offset points")
        ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.0%})")
        ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.0%})")
        ax.set_title(title)
        fig.colorbar(sc, label=target)
        fig.tight_layout()
        fig.savefig(f"figures/{fname}", dpi=160,
                    bbox_inches="tight", pad_inches=0.15)
        plt.close(fig)
        print("wrote", fname)


if __name__ == "__main__":
    main()
