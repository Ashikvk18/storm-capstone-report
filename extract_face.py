"""Extract head-pose + attention features from the webcam overlay.

MediaPipe FaceLandmarker (pre-trained neural net) runs on the top-right
webcam region at 1 fps and estimates head yaw/pitch/roll plus face
position per second -> out/<name>_face.csv.

Requires face_landmarker.task in the repo root:
https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task

The video decode is shared with segment_sessions.py's cadence (1 fps)
but must re-read frames since framesig only stores scalars.

Also emits facial blendshape scores (action units: brow raise, jaw
drop, smile, frown, eye blink, ...) per detected face ->
out/<name>_blend.csv for expression-dynamics features.
"""
import glob
import math
import os
import sys

import cv2
import numpy as np
import pandas as pd

import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions

SAMPLE_SEC = 1.0
CAM_X0, CAM_X1 = 0.80, 1.00
CAM_Y0, CAM_Y1 = 0.00, 0.15


# blendshapes worth tracking: brows (confusion/surprise), eyes (blink =
# drowsiness/effort), mouth (smile/frown/jaw), nose (sneer = negative)
BLEND_KEYS = [
    "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
    "eyeBlinkLeft", "eyeBlinkRight",
    "jawOpen", "mouthSmileLeft", "mouthSmileRight",
    "mouthFrownLeft", "mouthFrownRight",
    "mouthPucker", "noseSneerLeft", "noseSneerRight",
    "cheekPuff", "mouthStretchLeft", "mouthStretchRight",
]


def head_pose(video):
    name = os.path.splitext(os.path.basename(video))[0]
    cache = f"out/{name}_face.csv"
    bcache = f"out/{name}_blend.csv"
    need_pose = not os.path.exists(cache)
    need_blend = not os.path.exists(bcache)
    if not need_pose and not need_blend:
        return
    fl = vision.FaceLandmarker.create_from_options(
        vision.FaceLandmarkerOptions(
            base_options=BaseOptions(
                model_asset_path="face_landmarker.task"),
            num_faces=1,
            output_facial_transformation_matrixes=True,
            output_facial_blendshapes=True))
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, int(round(fps * SAMPLE_SEC)))
    rows, brows = [], []
    idx = 0
    while idx < n:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, fr = cap.read()
        if not ok:
            break
        h, w = fr.shape[:2]
        cam = fr[int(h * CAM_Y0):int(h * CAM_Y1), int(w * CAM_X0):w]
        rgb = cv2.cvtColor(cam, cv2.COLOR_BGR2RGB)
        res = fl.detect(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        t = idx / fps
        if res.face_landmarks:
            lm = res.face_landmarks[0]
            m = res.facial_transformation_matrixes[0]
            # rotation matrix -> approximate Euler angles (degrees)
            yaw = math.degrees(math.atan2(m[2][0], m[0][0]))
            pitch = math.degrees(math.asin(-m[2][1]))
            roll = math.degrees(math.atan2(m[0][1], m[1][1]))
            cx = float(np.mean([p.x for p in lm]))
            cy = float(np.mean([p.y for p in lm]))
            fw = float((max(p.x for p in lm)
                        - min(p.x for p in lm)) * cam.shape[1])
            rows.append((t, 1, yaw, pitch, roll, cx, cy, fw))
            if res.facial_blendshapes:
                vals = {c.category_name: c.score
                        for c in res.facial_blendshapes[0]}
                brows.append((t, 1) + tuple(vals.get(k, 0.0)
                                            for k in BLEND_KEYS))
            else:
                brows.append((t, 1) + (0.0,) * len(BLEND_KEYS))
        else:
            rows.append((t, 0, np.nan, np.nan, np.nan,
                         np.nan, np.nan, np.nan))
            brows.append((t, 0) + (np.nan,) * len(BLEND_KEYS))
        idx += step
    cap.release()
    if need_pose:
        pd.DataFrame(rows, columns=["t_sec", "face_found", "yaw", "pitch",
                                    "roll", "face_cx", "face_cy",
                                    "face_w"]).to_csv(cache, index=False)
    if need_blend:
        pd.DataFrame(brows, columns=["t_sec", "face_found"]
                     + BLEND_KEYS).to_csv(bcache, index=False)
    print(f"  {name}: {sum(r[1] for r in rows)}/{len(rows)} faces",
          flush=True)


def main():
    videos = sorted(glob.glob("recovered/*.mp4"))
    if len(sys.argv) > 1:
        videos = [v for v in videos if sys.argv[1] in v]
    for v in videos:
        print(f"face <- {os.path.basename(v)}", flush=True)
        try:
            head_pose(v)
        except Exception as e:  # truncated/corrupt tails must not kill batch
            print(f"  !! {e}", flush=True)


if __name__ == "__main__":
    main()
