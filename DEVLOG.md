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

