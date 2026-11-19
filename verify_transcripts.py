"""Transcript-level verification: cross-check segmentation inputs.

verify.py checks the committed CSVs; this script checks the RAW
inputs they were built from - the .vtt transcripts and .mp4 durations.
Catches cases where segmentation silently consumed bad transcripts.

Checks per transcripted session:
  - landmark narration phrases are actually present in the VTT
  - "audio shared" speaker cues exist (app audio was transcribed)
  - last app cue ends before the recording duration
  - survival_call phase is present in session_segments
  - phase order in segments respects play order

Usage: python verify_transcripts.py
"""
import glob
import os
import re

import pandas as pd

LANDMARK_HINTS = ["welcome", "tornado formation", "tornado alley",
                  "what is a tornado", "vehicle", "basement"]
PHASE_ORDER = ["pre_app", "lesson1", "quiz1", "lesson2", "impacts",
               "survival_call", "survival_nav", "final_quiz",
               "post_app", "interview"]

RESULTS = []


def record(name, ok, detail=""):
    """Append one check result."""
    RESULTS.append((name, bool(ok), detail))


def parse_vtt_speakers(path):
    """Return (n_cues, n_audio_shared, first_t, last_t, text_blob)."""
    txt = open(path, encoding="utf-8", errors="replace").read()
    cues = re.findall(
        r"(\d{2}):(\d{2}):(\d{2})\.(\d{3}) --> "
        r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*\n(.+?)(?=\n\n|\Z)",
        txt, re.S)
    n_shared = 0
    first = last = None
    blob = []
    for h1, m1, s1, ms1, h2, m2, s2, ms2, body in cues:
        st = int(h1) * 3600 + int(m1) * 60 + int(s1)
        en = int(h2) * 3600 + int(m2) * 60 + int(s2)
        first = st if first is None else min(first, st)
        last = en if last is None else max(last, en)
        body = " ".join(body.split())
        blob.append(body.lower())
        if "audio shared" in body.lower():
            n_shared += 1
    return len(cues), n_shared, first, last, " ".join(blob)


def vtt_for(mp4):
    """Find the transcript paired with an mp4 by filename stem."""
    stem = mp4[:-4]
    for cand in (stem + ".transcript.vtt", stem + ".vtt"):
        if os.path.exists(cand):
            return cand
    return None


def check_counts():
    """Expect 20 mp4 and 19 vtt (P07 has no transcript)."""
    mp4s = glob.glob("recovered/*.mp4")
    # "*.vtt" already matches both "X.vtt" and "X.transcript.vtt"
    vtts = glob.glob("recovered/*.vtt")
    record("20 mp4 recordings found", len(mp4s) == 20,
           f"got {len(mp4s)}")
    record("19 transcripts found", len(vtts) == 19,
           f"got {len(vtts)}")


