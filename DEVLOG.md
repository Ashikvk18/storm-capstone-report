# DEVLOG — why the pipeline is built the way it is

This document explains every function, variable, and non-obvious condition in
the RQ2 analysis pipeline: what it does and, more importantly, *why* it exists.
Read alongside the code; each entry names the file and the construct.

Pipeline order:

```
extract_zip.py        -> recovered/*.mp4 + *.vtt   (rescue damaged archive)
build_labels.py       -> data/labels.csv           (survey -> outcome scores)
segment_sessions.py   -> out/*_timeline.csv, *_framesig.csv, data/session_segments.csv
extract_face.py       -> out/*_face.csv, *_blend.csv (ML head pose + expressions)
extract_features.py   -> data/features.csv         (behavioral features)
explore.py            -> data/explore_correlations.csv (feature x outcome)
model_rq2.py          -> data/model_coefficients.csv   (LASSO + LOO-CV)
make_figures.py       -> figures/*.png             (report visuals)
make_pca.py           -> figures/pca_*.png         (behavior profiles)
make_pdf.py           -> storm-capstone.pdf        (README -> PDF)
```

---

## extract_zip.py — rescuing a corrupted archive

The source `VR_Training_Zoom_Recordings.zip` (~5 GB) has a broken central
directory, so `zipfile` cannot open it. Entries are STORED (uncompressed)
with sizes in a trailing data descriptor — file data simply runs from each
local header to just before the next one, minus 12–16 descriptor bytes.

| Construct | Why |
|---|---|
| `ZIP_PATH`, `INDEX_PATH`, `OUT_DIR`, `DD_SIG` | Archive location, cache of the header scan (re-scanning 5 GB is slow), output folder, and the `PK\x07\x08` signature that marks a data descriptor. |
| `build_index()` | Scans the raw bytes for `PK\x03\x04` local-file-header signatures and records each entry's name + offsets. Reads in 64 MB chunks with a 400-byte `overlap` buffer because a header can straddle a chunk boundary — without the overlap, headers at chunk edges would be silently missed. |
| dedupe loop in `build_index()` | The overlap makes the same header visible in two chunks; `seen`/`uniq` drops the duplicate so each file is extracted once. |
| `data_end(f, next_offset)` | Decides where file data ends by checking whether the 4 bytes before the next header are the `PK\x07\x08` descriptor signature: 16-byte descriptor if present, else 12. Getting this wrong truncates or overruns every file. |
| `extract_entry()` | Copies bytes `[start, end)` in 8 MB chunks. Chunked because some videos are >1 GB — reading it all at once would blow memory. |
| last-entry special case in `main()` | There is no "next header" for the final entry, so the end is `zip_size` minus a possible trailing descriptor — checked directly at EOF. |
| `INDEX_PATH` cache | The 5 GB scan takes minutes; caching offsets to `_zip_index.json` makes re-extraction instant. |

## build_labels.py — survey answers -> outcome scores

| Construct | Why |
|---|---|
| `GUESS_MAP` | Maps the GUESS engagement survey's Likert *text* labels to 1–7. Includes `"strongy agree"` — a typo in the actual survey data that would otherwise silently score NaN. |
| `ENGAGEMENT_ITEMS = {"3","5","6","8","13","14"}` | The six GUESS items that measure focus/engrossment/motivation. Item 8 ("I feel bored") is **reverse-coded** — agreement means *less* engagement, so a high raw score must be flipped or the composite would be backwards. |
| `GUESS_REVERSED = {"8"}` | Same reverse-coding applied when scoring the full GUESS scale. |
| `CONFUSION_ITEMS = ["5"–"8"]` | The cognitive-load items asking whether explanations were unclear/ineffective — this composite is the "confusion" label. |
| `COMPLEXITY_ITEMS`, `PERCEIVED_LEARNING_ITEMS`, `EFFORT_ITEMS` | Other cognitive-load item groups kept as auxiliary outcomes so correlations can be checked against more than one label. |
| `EXCLUDE_NAMES` | Drops pilot/test rows (`test`, `testing`, `prabeen giri`) — researcher submissions that aren't real participants. |
| `load_qualtrics()` | `iloc[2:]` skips Qualtrics' two metadata rows (question text + import IDs) that would otherwise be scored as a respondent. |
| `norm_name()` / `to_pid()` | Survey names have typos vs. the recording list; fuzzy matching (`difflib`, cutoff 0.7) recovers the correct participant instead of dropping the row. |
| `guess_score()` | `8 - score` implements reverse coding for item 8; returns NaN (not 0) for missing answers so composites use `nanmean` and don't treat "unanswered" as "strongly disagree". |
| `cl_score()` | Cognitive-load items use anchor labels ("not at all"/"moderately"/"completely") instead of numbers; the prefix check maps them to 0/5/10 before falling back to float parsing. |
| `mc_correct()` | Substring matching because pre/post survey MC options are lettered differently between the two forms — the *content* is what matters. |
| `score_matching()` / `score_sequence()` | The drag-drop and re-sequence items are scored as *fraction correct* (of 3 terms / 4 stages), giving partial credit instead of all-or-nothing. |
| `knowledge_score()` | Combines 8 binary MC items + 2 fractional items = a 10-point knowledge score. `nansum` skips unanswered items rather than failing the whole score. |
| `MC_KEY` / `POST_COL` | The correct-answer substrings for each MC item, plus the column remap (`K1`→`Q2` etc.) because pre and post surveys number questions differently. |
| `cronbach_alpha()` | Internal-consistency reliability of the engagement/confusion composites — printed at runtime so we can report whether the labels are trustworthy (printed: engagement α≈.85, confusion α≈.80). |
| dedupe `pre` by name | Some participants submitted the pre-survey twice; `drop_duplicates(keep="first")` keeps the earliest submission. |
| `_key` join via `participant_id` | Joins pre and post rows on participant id (falling back to normalized name for survey-only respondents) — tolerates name typos *between* the two surveys. |
| `has_recording` | Flags survey respondents who have no video (e.g., P17 missing post-survey is handled on the label side). |
| `learning_gain = post - pre` | The learning outcome for RQ2 context. |
| dropping `survey_name` from output | PII — names/emails must not be committed; `participants.csv` stays local via `.gitignore`. |

