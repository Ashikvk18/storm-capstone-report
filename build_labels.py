"""Build data/labels.csv from the Qualtrics survey exports.

Outputs per-participant:
  - knowledge scores: pre (K1-K10), post (Q2-Q11), learning gain
  - engagement composite: GUESS items on focus/engrossment/motivation (1-7)
  - confusion composite: cognitive-load items on unclear explanations (0-10)
  - auxiliary composites: perceived learning, effort, content complexity,
    full GUESS score

Also prints Cronbach's alpha for the engagement and confusion item sets.

Participants are matched to recordings via data/participants.csv names
(fuzzy match to tolerate survey typos). Survey respondents with no
recording are kept with has_recording=False.
"""
import difflib
import os
import sys

import numpy as np
import pandas as pd

PRE_FILE = "Tornado_PreSurvey_Knowledge+others_May 19, 2026_06.44.xlsx"
POST_FILE = "Tornado_PostSurvey1_KnowledgeandMore_for BOTH_May 19, 2026_20.02.xlsx"
PARTICIPANTS = "data/participants.csv"
OUT_FILE = "data/labels.csv"

# P17's post-survey composites were supplied separately (not in the
# Qualtrics export); applied after the survey join so learning_gain
# stays consistent.
MANUAL_POST_SCORES = {
    "P17": {
        "post_score": 7.85, "engagement": 4.85, "confusion": 1.25,
        "perceived_learning": 7.68, "effort": 3.15, "complexity": 2.03,
        "guess_full": 4.85,
    }
}

GUESS_MAP = {
    "strongly disagree": 1, "disagree": 2, "somewhat disagree": 3,
    "neither disagree nor agree": 4, "somewhat agree": 5, "agree": 6,
    "strongly agree": 7, "strongy agree": 7,  # survey typo
}

# GUESS items for the engagement composite (Q12_GUX_n).
# 8 ("I feel bored") is reverse-coded.
ENGAGEMENT_ITEMS = {"3": 1, "5": 1, "6": 1, "8": -1, "13": 1, "14": 1}
GUESS_REVERSED = {"8"}  # for full-scale scoring too

# Cognitive-load items (Q15_n, 0-10): confusion = unclear/ineffective
# explanations; other groups kept as auxiliary composites.
CONFUSION_ITEMS = ["5", "6", "7", "8"]
COMPLEXITY_ITEMS = ["1", "2", "3"]
PERCEIVED_LEARNING_ITEMS = ["9", "10", "11", "12"]
EFFORT_ITEMS = ["4", "13"]

EXCLUDE_NAMES = {"test", "testing", "prabeen giri"}  # pilot/researcher rows


def load_qualtrics(path):
    """Read a Qualtrics export, dropping the 2 metadata rows."""
    df = pd.read_excel(path)
    df = df.iloc[2:].reset_index(drop=True)
    return df


def norm_name(s):
    return " ".join(str(s).split()).lower()


def to_pid(name, name_to_pid):
    """Map a survey name to a participant id (fuzzy for typos)."""
    n = norm_name(name)
    if n in name_to_pid:
        return name_to_pid[n]
    close = difflib.get_close_matches(n, list(name_to_pid), n=1, cutoff=0.7)
    return name_to_pid[close[0]] if close else None


def guess_score(row, item, reversed_=False):
    """Score one GUESS item (1-7); returns NaN if missing/unparseable."""
    v = row.get(f"Q12_GUX_{item}")
    if pd.isna(v):
        return np.nan
    s = str(v).strip().lower()
    score = GUESS_MAP.get(s, np.nan)
    if reversed_ and not np.isnan(score):
        score = 8 - score
    return score


def cl_score(row, item):
    """Score one cognitive-load item (0-10) with anchor-label handling."""
    v = row.get(f"Q15_{item}")
    if pd.isna(v):
        return np.nan
    s = str(v).strip().lower()
    for label, val in (("not at all", 0), ("moderately", 5), ("completely", 10)):
        if s.startswith(label):
            return float(val)
    try:
        return float(s)
    except ValueError:
        return np.nan


def mc_correct(answer, needle):
    """Multiple choice scored by substring (letters differ between forms)."""
    if pd.isna(answer):
        return np.nan
    return float(needle in str(answer).lower())


def score_matching(row, prefix):
    """Drag-drop item: fraction of 3 terms matched to right description."""
    key = {0: "supercell", 1: "wind shear", 2: "updraft"}
    vals = []
    for grp, term in key.items():
        v = row.get(f"{prefix}_{grp}_GROUP")
        vals.append(np.nan if pd.isna(v) else float(term in str(v).lower()))
    return np.nanmean(vals) if any(not np.isnan(x) for x in vals) else np.nan


def score_sequence(row, prefix):
    """Re-sequence item: fraction of 4 stages in the correct position."""
    # correct rank for each stage column: 1=touchdown, 2=warm air,
    # 3=wind shear, 4=column tightens
    key = {1: 4, 2: 1, 3: 2, 4: 3}
    vals = []
    for col, correct_rank in key.items():
        v = row.get(f"{prefix}_{col}")
        try:
            vals.append(float(int(v) == correct_rank))
        except (TypeError, ValueError):
            vals.append(np.nan)
    return np.nanmean(vals) if any(not np.isnan(x) for x in vals) else np.nan


def knowledge_score(row, prefix_map):
    """10-point knowledge score.

    prefix_map: dict of scoring functions -> column prefix in this form
    (K for pre, Q for post).
    """
    parts = []
    for col, needle in prefix_map["mc"]:
        parts.append(mc_correct(row.get(col), needle))
    parts.append(score_matching(row, prefix_map["match"]))
    parts.append(score_sequence(row, prefix_map["seq"]))
    if all(pd.isna(p) for p in parts):
        return np.nan
    return float(np.nansum(parts))  # 8 single pts + 2 fractional items = 10


# (column, substring-that-means-correct) for the 8 single-point MC items.
# Column names are identical in pre (K1-K10) and post (Q2-Q11) forms.
MC_KEY = [
    ("K1", "warm, moist gulf"),      # -> Q2
    ("K2", "gulf of mexico"),        # -> Q3
    ("K3", "basement"),              # -> Q4
    ("K6", "true"),                  # -> Q7  funnel-touchdown definition
    ("K7", "spring"),                # -> Q8  season
    ("K8", "cumulonimbus"),          # -> Q9  cloud type
    ("K9", "texas"),                 # -> Q10 ~150/year state
    ("K10", "picks up dirt"),        # -> Q11 darker funnel
]
POST_COL = {"K1": "Q2", "K2": "Q3", "K3": "Q4", "K6": "Q7", "K7": "Q8",
            "K8": "Q9", "K9": "Q10", "K10": "Q11"}


def cronbach_alpha(df):
    """Cronbach's alpha of an item matrix (rows=respondents)."""
    df = df.dropna()
    k = df.shape[1]
    if k < 2 or len(df) < 2:
        return np.nan
    var_sum = df.var(axis=0, ddof=1).sum()
    total_var = df.sum(axis=1).var(ddof=1)
    return float(k / (k - 1) * (1 - var_sum / total_var))


def main():
    parts = pd.read_csv(PARTICIPANTS)
    name_to_pid = {norm_name(n): p for n, p in
                   zip(parts["name"], parts["participant_id"])}

    pre = load_qualtrics(PRE_FILE)
    post = load_qualtrics(POST_FILE)

    # dedupe pre-survey: keep first submission per normalized name
    pre["_n"] = pre["D1"].map(norm_name)
    pre = pre[~pre["_n"].isin(EXCLUDE_NAMES)]
    pre = pre.sort_values("StartDate").drop_duplicates("_n", keep="first")
    post["_n"] = post["Q1"].map(norm_name)
    post = post[~post["_n"].isin(EXCLUDE_NAMES)]

    post_mc = [(POST_COL[c], n) for c, n in MC_KEY]
    rows = []
    for _, pr in pre.iterrows():
        pid = to_pid(pr["D1"], name_to_pid)
        pre_score = knowledge_score(
            pr, {"mc": MC_KEY, "match": "K4", "seq": "K5"})
        rows.append({"participant_id": pid, "survey_name": pr["D1"],
                     "pre_score": pre_score})
    df = pd.DataFrame(rows)

    post_rows = []
    for _, pr in post.iterrows():
        pid = to_pid(pr["Q1"], name_to_pid)
        eng = [guess_score(pr, i, r < 0) for i, r in ENGAGEMENT_ITEMS.items()]
        conf = [cl_score(pr, i) for i in CONFUSION_ITEMS]
        guess_all = [guess_score(pr, str(i), str(i) in GUESS_REVERSED)
                     for i in range(1, 19)]
        post_rows.append({
            "participant_id": pid,
            "_n": norm_name(pr["Q1"]),
            "post_score": knowledge_score(
                pr, {"mc": post_mc, "match": "Q5", "seq": "Q6"}),
            "engagement": np.nanmean(eng),
            "confusion": np.nanmean(conf),
            "perceived_learning": np.nanmean(
                [cl_score(pr, i) for i in PERCEIVED_LEARNING_ITEMS]),
            "effort": np.nanmean([cl_score(pr, i) for i in EFFORT_ITEMS]),
            "complexity": np.nanmean(
                [cl_score(pr, i) for i in COMPLEXITY_ITEMS]),
            "guess_full": np.nanmean(guess_all),
            "_eng_items": eng, "_conf_items": conf,
        })
    postdf = pd.DataFrame(post_rows)

    # reliability of the two label composites
    eng_mat = pd.DataFrame([r for r in postdf["_eng_items"]])
    conf_mat = pd.DataFrame([r for r in postdf["_conf_items"]])
    print(f"Cronbach alpha  engagement(6 items) = {cronbach_alpha(eng_mat):.3f}")
    print(f"Cronbach alpha  confusion(4 items)  = {cronbach_alpha(conf_mat):.3f}")

    postdf = postdf.drop(columns=["_eng_items", "_conf_items"])
    # join key: participant_id when the person is a recorded participant,
    # else the normalized survey name (survey-only respondents). Using pid
    # tolerates name typos between the two surveys (e.g. 'jiauxan he').
    df["_key"] = df["participant_id"].fillna(
        "nr_" + df["survey_name"].map(norm_name))
    postdf["_key"] = postdf["participant_id"].fillna("nr_" + postdf["_n"])
    df = df.merge(postdf.drop(columns=["_n"]), on="_key", how="outer",
                  suffixes=("", "_post"))
    df["participant_id"] = df["participant_id"].fillna(
        df["participant_id_post"])
    df = df.drop(columns=["_key", "participant_id_post"])
    for pid, vals in MANUAL_POST_SCORES.items():
        m = (df["participant_id"] == pid) & df["post_score"].isna()
        for col, val in vals.items():
            df.loc[m, col] = val
    df["has_recording"] = df["participant_id"].notna()
    df["learning_gain"] = df["post_score"] - df["pre_score"]
    df = df.sort_values("participant_id", na_position="last")

    os.makedirs("data", exist_ok=True)
    # survey_name is PII - keep it out of the committed CSV
    df.drop(columns=["survey_name"]).to_csv(OUT_FILE, index=False)
    print(f"\nwrote {OUT_FILE} ({len(df)} rows)")
    print(df[["participant_id", "survey_name", "pre_score", "post_score",
              "learning_gain", "engagement", "confusion",
              "has_recording"]].to_string(index=False))


if __name__ == "__main__":
    main()
