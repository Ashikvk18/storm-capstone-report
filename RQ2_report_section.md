# RQ2: Explainable Behavioral Features of Engagement and Confusion in Immersive VR Learning

## 1. Introduction

Immersive VR learning environments generate rich behavioral data — where
learners look, how long they dwell, whether they retry, how they move —
yet most studies lack the telemetry to capture it. This study asked:

> **RQ2:** Which explainable behavioral features are indicative of
> cognitive engagement and confusion in immersive VR learning
> environments?

The Storm capstone app (Unity VR tornado-safety curriculum) produced **no
in-app logs**. The only behavioral record was a set of Zoom screen
recordings: fullscreen app footage, a webcam overlay of the participant,
and auto-generated transcripts of app narration and post-session
interviews. We therefore built a complete video-observation pipeline —
archive recovery, phase segmentation, rule-based and ML-derived feature
extraction — and related the resulting behaviors to post-session survey
labels.

## 2. Method

### 2.1 Data

- **20 session recordings** (MP4 + VTT transcript), Jan–Apr 2026,
  recovered from a damaged ~5 GB ZIP via stream-level extraction
  (`extract_zip.py`).
- **19 participants** usable for labeled analysis: P17 lacked a
  post-survey; P07's recording was truncated mid-session with no
  transcript (kept as missing data, not zeros).
- Survey instruments: pre/post 10-item tornado-knowledge tests, a GUESS
  game-experience scale, and a cognitive-load scale (composites:
  engagement, confusion, perceived learning, effort, complexity,
  learning gain).

