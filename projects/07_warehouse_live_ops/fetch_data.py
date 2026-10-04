#!/usr/bin/env python3
"""Download the two warehouse recordings this project runs on.

Source: NVIDIA PhysicalAI-SmartSpaces, subset MTMC_Tracking_2026, CC BY 4.0,
no account or token needed.

  warehouse_000   train split, 19 cameras, synthetic, with 3D labels and a
                  top-down floor plan
  warehouse_027   test split, 7 cameras, a real warehouse, calibration only

Every file is listed through the Hugging Face API first, so each download is
checked against its published size: a complete file is skipped and a partial
one is fetched again. Depth maps are never fetched - they are 185 GB for one
scene and nothing here reads them.

    python fetch_data.py                       # both scenes, ~3.6 GB
    python fetch_data.py --scene warehouse_027
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from config import SOURCES, input_dir  # noqa: E402

REPO = "nvidia/PhysicalAI-SmartSpaces"
API = f"https://huggingface.co/api/datasets/{REPO}/tree/main/"
RAW = f"https://huggingface.co/datasets/{REPO}/resolve/main/"
AGENT = {"User-Agent": "warehouse-live-ops/1.0 (+https://github.com/sndypvtra/coba_coba)"}
SKIP = ("depth_map",)


def listing(path: str) -> list[dict]:
    req = urllib.request.Request(f"{API}{path}?recursive=true", headers=AGENT)
    with urllib.request.urlopen(req, timeout=120) as r:
        return [e for e in json.load(r) if e["type"] == "file"
                and not any(s in e["path"] for s in SKIP)]


def fetch(url: str, dst: Path, size: int) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    part = dst.with_suffix(dst.suffix + ".part")
    req = urllib.request.Request(url, headers=AGENT)
    done = 0
    with urllib.request.urlopen(req, timeout=120) as r, open(part, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
    if done != size:
        raise IOError(f"{dst.name}: got {done} bytes, expected {size}")
    part.replace(dst)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", choices=list(SOURCES), action="append",
                    help="fetch only this scene (repeatable); default: all")
    args = ap.parse_args()

    for key in args.scene or list(SOURCES):
        src = SOURCES[key]
        root = input_dir(key)
        files = listing(src.hf_path)
        total = sum(e["size"] for e in files)
        print(f"{key}: {len(files)} files, {total / 1e9:.2f} GB -> {root}")
        for e in files:
            rel = e["path"][len(src.hf_path) + 1:]
            dst = root / rel
            if dst.exists() and dst.stat().st_size == e["size"]:
                print(f"  present  {rel}")
                continue
            print(f"  fetch    {rel}  ({e['size'] / 1e6:.0f} MB)", flush=True)
            fetch(RAW + e["path"], dst, e["size"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
