"""Extract per-session behavioral features -> data/features.csv (RQ2).

Inputs per recording:
  out/<name>_timeline.csv   per-second phase labels (segment_sessions.py)
  recovered/<name>.vtt      transcript (quiz correctness feedback)
  recovered/<name>.mp4      video (webcam-corner motion, whole-frame motion)

Feature groups:
  timing   - session span + dwell in each phase
  quiz     - n correct / incorrect feedback cues, quiz duration
  webcam   - motion energy + stillness ratio (disengagement proxy)
  motion   - whole-frame motion (sanity / animation-activity check)
"""
import glob
import os
import re
import sys

import cv2
import numpy as np
import pandas as pd

SAMPLE_SEC = 1.0
# webcam overlay occupies the top-right corner (Zoom layout)
CAM_X0, CAM_X1 = 0.80, 1.00
CAM_Y0, CAM_Y1 = 0.00, 0.15
STILL_EPS = 1.2          # mean abs pixel diff below this = "still"
SESSION_PHASES = ["pre_app", "lesson1", "quiz1", "lesson2", "impacts",
                  "survival_call", "survival_nav", "final_quiz",
                  "post_app"]

CORRECT_RE = re.compile(r"\b(that is (absolutely )?correct|correct\.)", re.I)
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


def motion_stats(video):
    """Per-second mean abs diff for webcam corner and whole frame."""
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, int(round(fps * SAMPLE_SEC)))
    prev = prev_cam = None
    cam_vals, full_vals, times = [], [], []
    idx = 0
    while idx < n:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, fr = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(cv2.resize(fr, (320, 180)), cv2.COLOR_BGR2GRAY)
        h, w = g.shape
        cam = g[int(h * CAM_Y0):int(h * CAM_Y1), int(w * CAM_X0):int(w * CAM_X1)]
        if prev is not None:
            full_vals.append(float(np.abs(g.astype(int) - prev.astype(int)).mean()))
            cam_vals.append(float(np.abs(cam.astype(int)
                                    - prev_cam.astype(int)).mean()))
            times.append(idx / fps)
        prev, prev_cam = g, cam
        idx += step
    cap.release()
    return np.array(times), np.array(full_vals), np.array(cam_vals)


def session_window(tl):
    """(start,end) of app usage: first to last non-desktop/non-interview."""
    in_app = tl["phase"].isin(SESSION_PHASES)
    if not in_app.any():
        return None, None
    return tl.loc[in_app, "t_sec"].min(), tl.loc[in_app, "t_sec"].max()


def extract_one(video, pid):
    name = os.path.splitext(os.path.basename(video))[0]
    tl_path = f"out/{name}_timeline.csv"
    if not os.path.exists(tl_path):
        return {"participant_id": pid, "file": name, "error": "no timeline"}
    tl = pd.read_csv(tl_path)
    vtt = next((c for c in (video[:-4] + ".transcript.vtt",
                            video[:-4] + ".vtt") if os.path.exists(c)), None)
    cues = parse_vtt(vtt) if vtt else []

    feat = {"participant_id": pid, "file": name}
    counts = tl["phase"].value_counts()
    for ph in SESSION_PHASES:
        feat[f"{ph}_s"] = int(counts.get(ph, 0))

    s0, s1 = session_window(tl)
    feat["session_s"] = (s1 - s0) if s0 is not None else np.nan

    # quiz feedback windows: quiz1 span and final_quiz span
    def span(phase):
        seg = tl[tl["phase"] == phase]
        return (seg["t_sec"].min(), seg["t_sec"].max()) if len(seg) else (0, 0)

    q1a, q1b = span("quiz1")
    fqa, fqb = span("final_quiz")
    feat["quiz1_correct"], feat["quiz1_wrong"] = quiz_feedback(cues, q1a, q1b)
    feat["finalq_correct"], feat["finalq_wrong"] = quiz_feedback(
        cues, fqa, fqb)

    # motion stats restricted to the app session window
    times, full_m, cam_m = motion_stats(video)
    m = (times >= s0) & (times <= s1) if s0 is not None else np.ones(
        len(times), bool)
    feat["webcam_motion_mean"] = float(cam_m[m].mean()) if m.any() else np.nan
    still = cam_m[m] < STILL_EPS
    feat["webcam_still_ratio"] = float(still.mean()) if m.any() else np.nan
    # longest consecutive still streak (seconds)
    longest = run = 0
    for v in still:
        run = run + 1 if v else 0
        longest = max(longest, run)
    feat["webcam_longest_still_s"] = longest
    feat["frame_motion_mean"] = float(full_m[m].mean()) if m.any() else np.nan
    return feat


def main():
    parts = pd.read_csv("data/participants.csv")

    def pid_of(name):
        for pid, f in zip(parts["participant_id"], parts["recording_file"]):
            if os.path.splitext(f)[0] == name:
                return pid
        return None

    videos = sorted(glob.glob("recovered/*.mp4"))
    if len(sys.argv) > 1:
        videos = [v for v in videos if sys.argv[1] in v]
    rows = []
    for v in videos:
        name = os.path.basename(v)
        print(f"features <- {name}", flush=True)
        rows.append(extract_one(v, pid_of(os.path.splitext(name)[0])))
    df = pd.DataFrame(rows)
    df.to_csv("data/features.csv", index=False)
    print(f"\nwrote data/features.csv ({len(df)} sessions)")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
