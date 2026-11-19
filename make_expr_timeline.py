"""P02 expression timeline: facial action units aligned to session phases.

Case-study figure for RQ2: does P02's face show confusion-related
expressions (frown, brow-raise, jaw-drop) during the ~8.5 min failed
survival navigation and the scenario replay?

Reads the per-second blendshape CSV (extract_face.py) and the phase
timeline (segment_sessions.py), smooths each action unit, and plots
them over a phase-band background.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

STEM = "2026-01-20_StorM_P02_Kamsi Amaeshi"
BLEND_CSV = f"out/{STEM}_blend.csv"
TIMELINE_CSV = f"out/{STEM}_timeline.csv"
OUT_PNG = "figures/p02_expressions.png"

