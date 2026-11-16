"""Pilot: segment a Storm session recording into coarse phases.

Samples frames at ~1 fps, computes simple per-frame signatures, and labels
each second as desktop/app and (roughly) which lesson phase is showing.
Outputs a per-second timeline CSV and a contact sheet of candidate
transition frames for visual verification.

Usage: python pilot_segment.py recovered/0217_P8.mp4
"""
import csv
import os
import sys

import cv2
import numpy as np

SAMPLE_EVERY_SEC = 1.0
THUMB_W, THUMB_H = 480, 270


def frame_signature(bgr):
    """Compact per-frame signature used for phase classification."""
    small = cv2.resize(bgr, (320, 180))
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    mean_v = float(v.mean())
    mean_s = float(s.mean())
    frac_white = float(((v > 200) & (s < 40)).mean())   # bright UI / explorer
    frac_dark = float((v < 60).mean())                  # night scene
    frac_teal = float(((h > 75) & (h < 100) & (s > 60) & (v > 90)).mean())
    # survival-scene choice buttons are muted teal panels
    # bottom strip: orange "Controls:" bar appears in survival scene
    bottom = hsv[160:180, :, :]
    bh, bs, bv = cv2.split(bottom)
    frac_orange = float(((bh < 20) & (bs > 120) & (bv > 120)).mean())
    return dict(mean_v=mean_v, mean_s=mean_s, frac_white=frac_white,
                frac_dark=frac_dark, frac_teal=frac_teal, frac_orange=frac_orange)


def classify(sig):
    """Rule-based coarse label from a frame signature."""
    if sig["frac_white"] > 0.45:
        return "desktop"          # file explorer / browser / bright OS windows
    if sig["frac_teal"] > 0.03 or sig["frac_orange"] > 0.05:
        return "survival_or_quiz"  # distinctive UI panels
    if sig["frac_dark"] > 0.35:
        return "dark_scene"        # storm/survival night footage
    return "app_scene"             # map, storm formation, other app footage


def main():
    video = sys.argv[1]
    base = os.path.splitext(os.path.basename(video))[0]
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        sys.exit(f"cannot open {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, int(round(fps * SAMPLE_EVERY_SEC)))

    rows, thumbs, thumb_t = [], [], []
    idx = 0
    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            break
        t = idx / fps
        sig = frame_signature(frame)
        sig["t_sec"] = round(t, 1)
        sig["label"] = classify(sig)
        rows.append(sig)
        idx += step

    cap.release()
    os.makedirs("out", exist_ok=True)
    csv_path = f"out/{base}_timeline.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} samples -> {csv_path}")

    # summarize contiguous segments per label
    segs = []
    cur, start = rows[0]["label"], rows[0]["t_sec"]
    for r in rows[1:]:
        if r["label"] != cur:
            segs.append((cur, start, r["t_sec"]))
            cur, start = r["label"], r["t_sec"]
    segs.append((cur, start, rows[-1]["t_sec"]))
    print("\n--- segments (label: start-end, dur) ---")
    for lab, a, b in segs:
        if b - a >= 2:
            print(f"{lab:16s} {a:7.0f}s - {b:7.0f}s  ({b-a:6.0f}s)")

    # contact sheet: frame at midpoint of each segment >= 5s
    cap = cv2.VideoCapture(video)
    picks = [(lab, (a + b) / 2) for lab, a, b in segs if b - a >= 5]
    tiles = []
    for lab, t in picks:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
        ok, fr = cap.read()
        if not ok:
            continue
        fr = cv2.resize(fr, (THUMB_W, THUMB_H))
        cv2.putText(fr, f"{lab} @{t:.0f}s", (8, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        tiles.append(fr)
    cap.release()
    cols = 3
    rows_n = (len(tiles) + cols - 1) // cols
    sheet = np.zeros((rows_n * THUMB_H, cols * THUMB_W, 3), np.uint8)
    for i, tl in enumerate(tiles):
        r, c = divmod(i, cols)
        sheet[r * THUMB_H:(r + 1) * THUMB_H, c * THUMB_W:(c + 1) * THUMB_W] = tl
    sheet_path = f"out/{base}_segments.jpg"
    cv2.imwrite(sheet_path, sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])
    print(f"\ncontact sheet -> {sheet_path}")


if __name__ == "__main__":
    main()
