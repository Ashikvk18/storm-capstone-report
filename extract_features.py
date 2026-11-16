"""Extract per-session behavioral features -> data/features.csv (RQ2).

Inputs per recording (all produced/cached by segment_sessions.py):
  out/<name>_timeline.csv   per-second phase labels
  out/<name>_framesig.csv   per-second desktop flag + frame/cam motion
  recovered/<name>.vtt      transcript (verbalized quiz feedback)

Feature groups:
  timing    - app session span + dwell per phase, pre-app menu time
  retries   - survival scenario re-attempts, aborted-run seconds
  quiz      - correct/incorrect feedback cues in quiz1 & final_quiz
  speech    - participant utterance time inside the app session
  webcam    - motion energy, stillness ratio, longest still streak;
              contrast between passive lessons and active navigation
  flags     - no_transcript, transcript_gap, incomplete recording
"""
import glob
import os
import re
import sys

import numpy as np
import pandas as pd

STILL_EPS = 1.2          # mean abs pixel diff below this = "still"
GAP_HEAD_S = 120         # pre_app longer than this = untranscribed head

# labels that mean "the Storm app (or its window) was on screen"
APP_LABELS = {"pre_app", "post_app", "app_idle", "aborted",
              "app_no_transcript", "participant_speech",
              "lesson1", "quiz1", "lesson2", "impacts",
              "survival_call", "survival_nav", "final_quiz"}
# scripted content phases in play order
PHASES = ["lesson1", "quiz1", "lesson2", "impacts",
          "survival_call", "survival_nav", "final_quiz"]
LESSON_PHASES = ["lesson1", "lesson2", "impacts"]

CORRECT_RE = re.compile(
    r"\b(that is (absolutely )?correct|correct\.|well done)", re.I)
INCORRECT_RE = re.compile(r"\bincorrect\b", re.I)


def parse_vtt(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    cues = []
    for m in re.finditer(
            r"(\d{2}):(\d{2}):(\d{2})\.(\d{3}) --> (\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*\n(.+?)(?=\n\n|\Z)",
            txt, re.S):
        h1, m1, s1, ms1, h2, m2, s2, ms2, body = m.groups()
        start = int(h1) * 3600 + int(m1) * 60 + int(s1) + int(ms1) / 1000
        end = int(h2) * 3600 + int(m2) * 60 + int(s2) + int(ms2) / 1000
        cues.append((start, end, " ".join(body.split())))
    return cues


def quiz_feedback(cues, t0, t1):
    """Count correct/incorrect feedback within a time window."""
    c = i = 0
    for s, e, text in cues:
        if e < t0 or s > t1:
            continue
        t = text.lower()
        if INCORRECT_RE.search(t):
            i += 1
        elif CORRECT_RE.search(t):
            c += 1
    return c, i


def runs(tl, phase, merge_gap=10):
    """Number of attempts: contiguous runs of a phase, merging runs
    separated by < merge_gap seconds (a 2s participant_speech blip must
    not split one survival call into two 'attempts')."""
    labels = tl["phase"].to_numpy()
    spans = []
    i = 0
    while i < len(labels):
        if labels[i] == phase:
            j = i
            while j < len(labels) and labels[j] == phase:
                j += 1
            spans.append((i, j))
            i = j
        else:
            i += 1
    merged = 0
    last_end = -merge_gap
    for s, e in spans:
        if s - last_end >= merge_gap:
            merged += 1
        last_end = e
    return merged


def span(tl, phase):
    seg = tl[tl["phase"] == phase]
    return (seg["t_sec"].min(), seg["t_sec"].max()) if len(seg) else (0, 0)


def extract_one(video, pid):
    name = os.path.splitext(os.path.basename(video))[0]
    tl_path = f"out/{name}_timeline.csv"
    if not os.path.exists(tl_path):
        return {"participant_id": pid, "error": "no timeline"}
    tl = pd.read_csv(tl_path)
    vtt = next((c for c in (video[:-4] + ".transcript.vtt",
                            video[:-4] + ".vtt") if os.path.exists(c)), None)
    cues = parse_vtt(vtt) if vtt else []
    sig = pd.read_csv(f"out/{name}_framesig.csv")

    feat = {"participant_id": pid}
    counts = tl["phase"].value_counts()
    for ph in PHASES:
        feat[f"{ph}_s"] = int(counts.get(ph, 0))
    for ph in ("pre_app", "post_app", "app_idle", "aborted",
               "app_no_transcript", "interview"):
        feat[f"{ph}_s"] = int(counts.get(ph, 0))

    # censor phases that ran during an untranscribed head (P04) or a
    # transcript-less recording (P07): their durations are unknown,
    # not zero
    feat["no_transcript"] = int(feat["app_no_transcript_s"] > 0)
    feat["transcript_gap"] = int(
        feat["pre_app_s"] > GAP_HEAD_S and feat["lesson1_s"] == 0)
    if feat["no_transcript"]:
        for ph in PHASES:
            feat[f"{ph}_s"] = np.nan
    elif feat["transcript_gap"]:
        gap_end = feat["pre_app_s"]
        for ph in PHASES:
            seg = tl.loc[tl["phase"] == ph, "t_sec"]
            if len(seg) == 0 or seg.min() <= gap_end:
                feat[f"{ph}_s"] = np.nan

    # session window: first non-desktop frame to sustained-desktop onset
    # (the same 30s rule used by segment_sessions.py); without a desktop
    # takeover the session runs to the last labeled app second
    times = sig["t_sec"].to_numpy()
    is_desk = sig["is_desktop"].to_numpy()
    onset = np.nan
    run = 0
    for i, d in enumerate(is_desk):
        run = run + 1 if d else 0
        if run >= 30:
            onset = times[i - 29]
            break
    first_app_mask = ~is_desk
    s0 = times[first_app_mask].min() if first_app_mask.any() else np.nan
    iv_secs = tl.loc[tl["phase"] == "interview", "t_sec"]
    iv0 = iv_secs.min() if len(iv_secs) else np.nan
    ends = [v for v in (onset, iv0) if not np.isnan(v)]
    if ends:
        s1 = min(ends)
    else:
        app_secs = tl[tl["phase"].isin(APP_LABELS)]["t_sec"]
        s1 = app_secs.max() if len(app_secs) else np.nan
    feat["session_s"] = (s1 - s0) if not np.isnan(s1) else np.nan

    # participant speech restricted to the session window
    sp = tl[(tl["phase"] == "participant_speech")
            & (tl["t_sec"] >= s0) & (tl["t_sec"] <= s1)]
    feat["speech_in_session_s"] = int(len(sp))

    # retries / restarts
    feat["survival_attempts"] = runs(tl, "survival_call")
    feat["was_restarted"] = int(feat["aborted_s"] > 0)

    # data-quality flags
    feat["reached_end"] = int(
        feat["final_quiz_s"] > 0 or feat["post_app_s"] > 0
        or feat["interview_s"] > 0)

    # quiz feedback inside the detected quiz windows (NaN if the window
    # itself was unobserved)
    for pre, phase in (("quiz1", "quiz1"), ("finalq", "final_quiz")):
        a, b = span(tl, phase)
        if b > a:
            c, w = quiz_feedback(cues, a, b)
            feat[f"{pre}_correct"], feat[f"{pre}_wrong"] = c, w
        else:
            feat[f"{pre}_correct"] = feat[f"{pre}_wrong"] = np.nan

    # motion stats restricted to the app session window
    cam_m = sig["cam_motion"].to_numpy()
    frame_m = sig["frame_motion"].to_numpy()
    win = (times >= s0) & (times <= s1) if not np.isnan(s1) \
        else np.zeros(len(times), bool)
    feat["webcam_motion_mean"] = float(cam_m[win].mean()) if win.any() else np.nan
    still = cam_m[win] < STILL_EPS
    feat["webcam_still_ratio"] = float(still.mean()) if win.any() else np.nan
    longest = run = 0
    for v in still:
        run = run + 1 if v else 0
        longest = max(longest, run)
    feat["webcam_longest_still_s"] = longest
    feat["frame_motion_mean"] = float(frame_m[win].mean()) if win.any() else np.nan

    # fidgeting during passive lessons vs active navigation
    for tag, mask_labels in (("lessons", LESSON_PHASES),
                             ("survival_nav", ["survival_nav"])):
        secs = tl[tl["phase"].isin(mask_labels)]["t_sec"].to_numpy()
        if len(secs):
            sel = np.isin(times, secs)
            feat[f"cam_motion_{tag}"] = float(cam_m[sel].mean()) \
                if sel.any() else np.nan
        else:
            feat[f"cam_motion_{tag}"] = np.nan
    return feat


def main():
    parts = pd.read_csv("data/participants.csv")
    stem_to_pid = {os.path.splitext(f)[0]: p
                   for p, f in zip(parts["participant_id"],
                                   parts["recording_file"])}

    videos = sorted(glob.glob("recovered/*.mp4"))
    if len(sys.argv) > 1:
        videos = [v for v in videos if sys.argv[1] in v]
    rows = []
    for v in videos:
        name = os.path.splitext(os.path.basename(v))[0]
        print(f"features <- {name}", flush=True)
        rows.append(extract_one(v, stem_to_pid.get(name)))
    df = pd.DataFrame(rows).sort_values("participant_id")
    df.to_csv("data/features.csv", index=False)
    print(f"\nwrote data/features.csv ({len(df)} sessions)")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
