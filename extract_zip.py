"""Extract entries from the damaged VR_Training_Zoom_Recordings.zip.

The archive's central directory is broken, so zipfile cannot open it.
Entries use flag 0x0808 with compression method 0 (STORED, uncompressed)
and sizes written in a trailing data descriptor. File data therefore runs
from each entry's data start to just before the next entry's local header,
minus the 12-16 byte data descriptor.

Usage:
    python extract_zip.py            # extract ALL entries to recovered/
    python extract_zip.py <name>     # extract one entry (substring match)
"""
import json
import os
import re
import sys

ZIP_PATH = "VR_Training_Zoom_Recordings.zip"
INDEX_PATH = "_zip_index.json"
OUT_DIR = "recovered"
DD_SIG = b"PK\x07\x08"  # data descriptor signature


def build_index():
    """Scan the archive for local file headers and record offsets."""
    entries = []
    pos_base = 0
    overlap = b""
    with open(ZIP_PATH, "rb") as f:
        while True:
            data = f.read(64 * 1024 * 1024)
            if not data:
                break
            buf = overlap + data
            for m in re.finditer(rb"PK\x03\x04", buf):
                i = m.start()
                abs_i = pos_base - len(overlap) + i
                if i + 30 > len(buf):
                    continue
                nlen = int.from_bytes(buf[i + 26 : i + 28], "little")
                elen = int.from_bytes(buf[i + 28 : i + 30], "little")
                if 0 < nlen < 300 and i + 30 + nlen <= len(buf):
                    name = buf[i + 30 : i + 30 + nlen]
                    try:
                        s = name.decode("utf-8")
                    except UnicodeDecodeError:
                        continue
                    if "/" in s or "." in s:
                        entries.append(
                            {
                                "name": s,
                                "offset": abs_i,
                                "data_offset": abs_i + 30 + nlen + elen,
                            }
                        )
            overlap = buf[-400:]
            pos_base += len(data)
    # drop accidental duplicates from overlap scanning
    seen, uniq = set(), []
    for e in entries:
        if e["offset"] not in seen:
            seen.add(e["offset"])
            uniq.append(e)
    return uniq


def data_end(f, next_offset):
    """Return the end offset of file data, stripping the data descriptor.

    The descriptor is 16 bytes (PK\\x07\\x08 + crc + csize + usize) when the
    signature is present, else 12 bytes.
    """
    f.seek(max(0, next_offset - 16))
    tail = f.read(16)
    if len(tail) == 16 and tail[:4] == DD_SIG:
        return next_offset - 16
    return next_offset - 12


def extract_entry(f, start, end, out_path):
    """Copy raw stored bytes in [start, end) to out_path."""
    f.seek(start)
    remaining = end - start
    with open(out_path, "wb") as out:
        while remaining > 0:
            chunk = f.read(min(8 * 1024 * 1024, remaining))
            if not chunk:
                break
            out.write(chunk)
            remaining -= len(chunk)
    return end - start - remaining


def main():
    if os.path.exists(INDEX_PATH):
        entries = json.load(open(INDEX_PATH))
    else:
        print("Scanning archive for file headers...")
        entries = build_index()
        json.dump(entries, open(INDEX_PATH, "w"), indent=1)
    print(f"{len(entries)} entries indexed")

    pattern = sys.argv[1] if len(sys.argv) > 1 else None
    targets = [e for e in entries if pattern is None or pattern in e["name"]]
    if not targets:
        print("No matching entry for:", pattern)
        return

    zip_size = os.path.getsize(ZIP_PATH)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(ZIP_PATH, "rb") as zf:
        for e in targets:
            idx = entries.index(e)
            next_off = (
                entries[idx + 1]["offset"] if idx + 1 < len(entries) else zip_size
            )
            if idx + 1 < len(entries):
                end = data_end(zf, next_off)
            else:
                # last entry: check for a data descriptor just before EOF
                zf.seek(zip_size - 16)
                tail = zf.read(16)
                end = zip_size - 16 if tail[:4] == DD_SIG else zip_size
            base = os.path.basename(e["name"])
            out_path = os.path.join(OUT_DIR, base)
            print(f"extracting {base} ({(end - e['data_offset'])/1e6:.0f} MB) ...",
                  flush=True)
            n = extract_entry(zf, e["data_offset"], end, out_path)
            print(f"  -> {n/1e6:.1f} MB written")


if __name__ == "__main__":
    main()
