#!/usr/bin/env bash
# Re-download the model weights and the three Pexels source clips.
# Both directories are gitignored, so run this after a fresh clone.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p weights videos

echo "== weights =="
for w in yoloe-11l-seg.pt yoloe-11m-seg.pt yolo11n-cls.pt; do
  [ -f "weights/$w" ] && { echo "  have $w"; continue; }
  echo "  fetching $w"
  curl -sSL --fail -o "weights/$w" \
    "https://github.com/ultralytics/assets/releases/download/v8.3.0/$w"
done

# The MobileCLIP text encoder (~572 MB) is fetched automatically by ultralytics
# the first time YOLOE.get_text_pe() runs, into the working directory.

echo "== source clips (Pexels, free for commercial use) =="
# Resolve the CDN file via the /download/ endpoint rather than guessing the
# filename: resolutions are irregular (5532772 is uhd_2732_1440, 7012967 is
# hd_1080_1350) and the HTML pages 403 to plain curl, but /download/ 302s
# straight to the real asset.
resolve () {
  curl -sS -o /dev/null -w '%{redirect_url}' --max-time 30 \
    "https://www.pexels.com/download/video/$1/"
}

# name|pexels-id
clips=(
  "01_oranges_production_line.mp4|10576687"
  "02_tomatoes_conveyor.mp4|8675102"
  "03_packages_conveyor.mp4|5370836"
)
for row in "${clips[@]}"; do
  IFS='|' read -r name id <<<"$row"
  [ -f "videos/$name" ] && { echo "  have $name"; continue; }
  url=$(resolve "$id")
  [ -z "$url" ] && { echo "  !! could not resolve pexels $id"; continue; }
  echo "  fetching $name (pexels $id)"
  curl -sSL --fail -o "videos/$name" "$url"
done

echo "done."
