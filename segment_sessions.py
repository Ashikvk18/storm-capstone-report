"""Segment each Storm session recording into phases.

Combines two sources:
  1. VTT transcript cues - 'Audio shared by Participant:' = in-app audio
     (narration). Keyword anchors locate lesson/quiz/survival boundaries.
     Other speakers (interviewers, 'Participant') = post-session interview.
  2. Frame sampling at 1fps - frac_white > 0.6 reliably flags desktop/
     browser windows vs the fullscreen app (brightest app sky ~0.48).

Outputs per session:
  out/<name>_timeline.csv  - per-second phase labels
  a verification contact sheet
And appends one summary row per session to data/session_segments.csv.

Phases (app order): pre_app, lesson1, quiz1, lesson2, impacts,
survival_call, survival_nav, final_quiz, post_app, interview, desktop
"""
import glob
import os
import re
import sys

import cv2
import numpy as np
import pandas as pd

SAMPLE_SEC = 1.0
DESKTOP_WHITE = 0.60
MIN_SEG = 3  # ignore segments shorter than this when summarizing

# Ordered landmark phrases found in narration (lower-case substrings).
# Each maps a cue to the phase that cue STARTS.
LANDMARKS = [
    ("welcome, learner", "lesson1"),
    ("exciting journey into the world of tornadoes", "lesson1"),
    ("which state in tornado alley sees the most tornadoes annually", "quiz1"),
    ("welcome to the tornado formation lesson", "lesson2"),
    ("tornadoes start with warm, moist air", "lesson2"),
    ("unleash incredible power", "impacts"),
    ("winds can reach speeds", "impacts"),
    ("vehicle unexpectedly breaks down", "survival_call"),
    ("on a journey when your vehicle", "survival_call"),
    ("what is a tornado?", "final_quiz"),
    ("which country gets the most tornadoes", "final_quiz"),
]

SURVIVAL_KW = ("mom", "honey", "basement", "church", "stranded",
               "broke down", "sturdy shelter", "get to that church",
               "warning sounds", "hurry")
IMPACTS_KW = ("damage", "power outage", "deadly threat", "rebuild",
              "billion", "devastating", "reshaping", "tearing through")
L2_KW = ("supercell", "cumulonimbus", "wind shear", "upper-level",
         "lower-level", "rotating column", "funnel", "moist air",
         "thunderstorm", "building blocks", "touches the ground",
         "debris", "tornadoes start")
L1_KW = ("tornado alley", "texas", "oklahoma", "kansas", "nebraska",
         "gulf of mexico", "canada", "central u.s", "hotspot",
         "150 tornadoes", "spring", "may and june", "flat plains",
         "twister")
QUIZ_FB = re.compile(r"\b(correct|incorrect|well done)\b", re.I)


def parse_vtt(path):
    """Return list of (start_sec, end_sec, speaker, text)."""
    txt = open(path, encoding="utf-8", errors="replace").read()
    cues = []
    for m in re.finditer(
            r"(\d{2}):(\d{2}):(\d{2})\.(\d{3}) --> (\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*\n(.+?)(?=\n\n|\Z)",
            txt, re.S):
        h1, m1, s1, ms1, h2, m2, s2, ms2, body = m.groups()
        start = int(h1) * 3600 + int(m1) * 60 + int(s1) + int(ms1) / 1000
        end = int(h2) * 3600 + int(m2) * 60 + int(s2) + int(ms2) / 1000
        body = " ".join(body.split())
        speaker, text = ("", body)
        if ": " in body:
            speaker, text = body.split(": ", 1)
        cues.append((start, end, speaker, text))
    return cues


def classify_app_cue(text):
    """Keyword-classify one in-app audio cue to a phase guess."""
    t = text.lower()
    if any(k in t for k in SURVIVAL_KW):
        return "survival_call"
    if QUIZ_FB.search(t) and len(t) < 60:
        return "quiz_fb"
    if any(k in t for k in IMPACTS_KW):
        return "impacts"
    if any(k in t for k in L2_KW):
        return "lesson2"
    if any(k in t for k in L1_KW):
        return "lesson1"
    return "app_other"


def anchor_phases(app_cues):
    """Assign a phase to each app-audio cue.

    Transitions are driven by landmark phrases (most reliable). Keyword
    classification is only a fallback for phases whose landmark never
    appears in this transcript - otherwise stray content words (e.g.
    'warm, moist air' inside lesson 1 narration) hijack the phase.
    """
    order = ["lesson1", "quiz1", "lesson2", "impacts", "survival_call",
             "final_quiz"]

    def landmark_of(text):
        t = text.lower()
        for phrase, ph in LANDMARKS:
            if phrase in t:
                return ph
        return None

    # which phases have a landmark hit anywhere in this transcript
    landmark_phases = {lm for _, _, t in app_cues
                       for lm in [landmark_of(t)] if lm}

    labeled = []
    cur = "lesson1"
    for start, end, text in app_cues:
        hit = landmark_of(text)
        if hit is None:
            guess = classify_app_cue(text)
            # fallback promotion only for landmark-missing phases
            if (guess in order and guess not in landmark_phases
                    and order.index(guess) > order.index(cur)):
                hit = guess
        if hit in order:
            if order.index(hit) < order.index(cur):
                # backward landmark = the app was restarted; the previous
                # run is a fragment and must not contaminate timings
                labeled = [(s, e, "aborted") for s, e, _ in labeled]
                cur = hit
            else:
                cur = hit
        labeled.append((start, end, cur))

    # split survival_call into dialogue vs navigation:
    #  - a scenario can be ATTEMPTED multiple times (the call replays);
    #    >20s of silence inside the survival block is navigation time,
    #    which also reveals retries as separate call clusters
    #  - some transcripts keep emitting 'Audio shared' cues through nav
    #    (game SFX/music) - call cues after the last keyword-bearing
    #    dialogue cue are navigation too
    call_idx = [i for i, (_, _, ph) in enumerate(labeled)
                if ph == "survival_call"]
    if call_idx:
        last_dialogue = labeled[call_idx[0]][1]
        for i in call_idx:
            s, e, _ = labeled[i]
            if any(k in app_cues[i][2].lower() for k in SURVIVAL_KW):
                last_dialogue = e
        labeled = [(s, e, "survival_nav" if ph == "survival_call"
                    and s >= last_dialogue else ph)
                   for s, e, ph in labeled]

    out = []
    for i, (s, e, ph) in enumerate(labeled):
        out.append((s, e, ph))
        nxt = labeled[i + 1] if i + 1 < len(labeled) else None
        if (ph in ("survival_call", "survival_nav") and nxt
                and nxt[0] - e > 20):
            out.append((e, nxt[0], "survival_nav"))
    return out


# webcam overlay occupies the top-right corner (Zoom layout)
CAM_X0, CAM_X1 = 0.80, 1.00
CAM_Y0, CAM_Y1 = 0.00, 0.15


def frame_flags(video):
    """Per-sample frame signature:
    (t_sec, is_desktop, frac_orange, frame_motion, cam_motion).

    Motion columns are mean abs pixel diff vs the previous sample -
    whole frame (app activity) and the webcam corner (participant
    movement). Caches the expensive decode to out/<name>_framesig.csv.
    """
    name = os.path.splitext(os.path.basename(video))[0]
    cache = f"out/{name}_framesig.csv"
    if os.path.exists(cache):
        df = pd.read_csv(cache)
        if "cam_motion" in df.columns:  # v2 cache
            return list(zip(df["t_sec"], df["is_desktop"].astype(bool),
                            df["frac_orange"], df["frame_motion"],
                            df["cam_motion"]))
        # v1 cache lacks motion - fall through and recompute
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, int(round(fps * SAMPLE_SEC)))
    out = []
    prev_g = prev_cam = None
    idx = 0
    while idx < n:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, fr = cap.read()
        if not ok:
            break
        small = cv2.resize(fr, (320, 180))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        frac_white = float(((v > 200) & (s < 40)).mean())
        bottom = hsv[160:180]
        bh, bs, bv = cv2.split(bottom)
        frac_orange = float(((bh < 20) & (bs > 120) & (bv > 120)).mean())
        g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        hh, ww = g.shape
        cam = g[int(hh * CAM_Y0):int(hh * CAM_Y1),
                int(ww * CAM_X0):int(ww * CAM_X1)]
        if prev_g is None:
            fm = cm = 0.0
        else:
            fm = float(np.abs(g.astype(int) - prev_g.astype(int)).mean())
            cm = float(np.abs(cam.astype(int)
                              - prev_cam.astype(int)).mean())
        prev_g, prev_cam = g, cam
        out.append((idx / fps, frac_white > DESKTOP_WHITE, frac_orange,
                    fm, cm))
        idx += step
    cap.release()
    os.makedirs("out", exist_ok=True)
    pd.DataFrame(out, columns=["t_sec", "is_desktop", "frac_orange",
                               "frame_motion", "cam_motion"]).to_csv(
        cache, index=False)
    return out


def desktop_onset(frames, sustain=30):
    """First second from which desktop persists for >= sustain seconds.

    Stray 'Audio shared' cues (interview chit-chat misattributed to
    shared audio) can appear long after the app closes - the frame
    stream is the trustworthy boundary.
    """
    run = 0
    for i, f in enumerate(frames):
        run = run + 1 if f[1] else 0
        if run >= sustain:
            return frames[i - sustain + 1][0]
    return None


def build_timeline(dur, app_cues, other_cues, frames):
    """Per-second label vector."""
    labels = ["app_idle"] * int(dur + 1)
    for t, is_desk, *_ in frames:
        if is_desk and int(t) < len(labels):
            labels[int(t)] = "desktop"
    last_app_end = app_cues[-1][1] if app_cues else 0
    # speech by real people: during the app session it is the participant
    # talking (engagement data); after the app ends it is the interview
    for s, e, _sp, _tx in other_cues:
        tag = "participant_speech" if s < last_app_end else "interview"
        for t in range(int(s), min(int(e) + 1, len(labels))):
            labels[t] = tag
    protected = ("desktop", "interview", "participant_speech")
    for s, e, ph in app_cues:
        for t in range(int(s), min(int(e) + 1, len(labels))):
            if labels[t] not in protected:
                labels[t] = ph
    # extend each phase across gaps to next phase start
    labeled_times = sorted({s for s, _, _ in app_cues})
    for i, s, e, ph in [(i, *x) for i, x in enumerate(app_cues)]:
        if ph == "aborted":
            continue  # leave gaps around aborted runs as app_idle
        nxt = labeled_times[i + 1] if i + 1 < len(labeled_times) else None
        end_fill = int(nxt) if nxt else int(e) + 1
        for t in range(int(s), min(end_fill, len(labels))):
            if labels[t] not in protected:
                labels[t] = ph
    if not app_cues:
        # no transcript (P07): every non-desktop frame is app content we
        # cannot phase-segment
        return ["desktop" if l == "desktop" else "app_no_transcript"
                for l in labels]
    first_app = app_cues[0][0]
    last_app = app_cues[-1][1]
    for t in range(len(labels)):
        if labels[t] == "app_idle":
            labels[t] = ("pre_app" if t < first_app else
                         "post_app" if t > last_app else "app_idle")
    return labels


def segments(labels):
    """Collapse per-second labels into (phase,start,end) segments."""
    segs = []
    cur, start = labels[0], 0
    for i, l in enumerate(labels[1:], 1):
        if l != cur:
            segs.append((cur, start, i))
            cur, start = l, i
    segs.append((cur, start, len(labels)))
    return [(p, a, b) for p, a, b in segs if b - a >= MIN_SEG]


def main():
    out_dir = "out"
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs("data", exist_ok=True)
    videos = sorted(glob.glob("recovered/*.mp4"))
    if len(sys.argv) > 1:
        videos = [v for v in videos if sys.argv[1] in v]
    summary = []
    for video in videos:
        name = os.path.splitext(os.path.basename(video))[0]
        vtt = None
        for cand in (video[:-4] + ".transcript.vtt", video[:-4] + ".vtt"):
            if os.path.exists(cand):
                vtt = cand
        cues = parse_vtt(vtt) if vtt else []
        app_cues_raw = [(s, e, t) for s, e, sp, t in cues
                        if "audio shared" in sp.lower()]
        other_cues = [(s, e, sp, t) for s, e, sp, t in cues
                      if "audio shared" not in sp.lower()]
        frames = frame_flags(video)
        onset = desktop_onset(frames)
        if onset is not None:
            app_cues_raw = [c for c in app_cues_raw if c[0] < onset]
        app_cues = anchor_phases(app_cues_raw)
        dur = frames[-1][0] if frames else 0
        labels = build_timeline(dur, app_cues, other_cues, frames)
        segs = segments(labels)

        pd.DataFrame({"t_sec": range(len(labels)), "phase": labels}).to_csv(
            f"{out_dir}/{name}_timeline.csv", index=False)
        row = {"file": name}
        for ph, a, b in segs:
            row.setdefault(f"{ph}_t", []).append((a, b))
        pid_m = re.search(r"P\d+", name)
        flat = {"pid": pid_m.group(0) if pid_m else name,
                "duration_s": int(dur)}
        for ph, spans in row.items():
            if ph == "file":
                continue
            flat[f"{ph}_start"] = spans[0][0]
            flat[f"{ph}_end"] = spans[-1][1]
            flat[f"{ph}_dur"] = sum(b - a for a, b in spans)
        summary.append(flat)
        print(f"\n=== {name} ({int(dur)}s) ===")
        for ph, a, b in segs:
            print(f"  {ph:14s} {a:5d}-{b:5d} ({b-a:4d}s)")

    sdf = pd.DataFrame(summary)
    sdf.to_csv("data/session_segments.csv", index=False)
    print(f"\nwrote data/session_segments.csv ({len(sdf)} sessions)")


if __name__ == "__main__":
    main()
