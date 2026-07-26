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
# name|pexels-id|cdn-filename
clips=(
  "01_oranges_production_line.mp4|10576687|10576687-hd_1920_1080_30fps.mp4"
  "02_tomatoes_conveyor.mp4|8675102|8675102-hd_1920_1080_30fps.mp4"
  "03_packages_conveyor.mp4|5370836|5370836-hd_1920_1080_30fps.mp4"
)
for row in "${clips[@]}"; do
  IFS='|' read -r name id file <<<"$row"
  [ -f "videos/$name" ] && { echo "  have $name"; continue; }
  echo "  fetching $name (pexels $id)"
  curl -sSL --fail -o "videos/$name" \
    "https://videos.pexels.com/video-files/${id}/${file}"
done

echo "done."
