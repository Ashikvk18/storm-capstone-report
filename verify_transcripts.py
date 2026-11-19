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


