#!/usr/bin/env bash
# Re-download the model weights and the four Pexels source clips.
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
# Every pipeline here is calibrated in pixels - counting lines and ROIs in
# factory_vision/counting/clips.py, the bottle geometry in factory_vision/filling/
# calibration.py - so the
# rendition matters, not just the clip. All four are calibrated on 1920x1080.
#
# The /download/ endpoint hands back the *largest* rendition, which is the right
# one for three of these but not for 8720278, where it is uhd_3840_2160. Name the
# variant we want and only fall back to the redirect if it has gone away.
#
# name|pexels-id|cdn-variant
clips=(
  "01_oranges_production_line.mp4|10576687|hd_1920_1080_30fps"
  "02_tomatoes_conveyor.mp4|8675102|hd_1920_1080_30fps"
  "03_packages_conveyor.mp4|5370836|hd_1920_1080_30fps"
  "07_bottle_filling_line.mp4|8720278|hd_1920_1080_25fps"
)

# The direct CDN path, if that rendition still exists.
cdn_url () {
  local url="https://videos.pexels.com/video-files/$1/$1-$2.mp4"
  curl -sS -o /dev/null -I --fail --max-time 30 "$url" && echo "$url"
}

# Fallback: the HTML pages 403 to plain curl, but /download/ 302s straight to
# the real asset.
resolve () {
  curl -sS -o /dev/null -w '%{redirect_url}' --max-time 30 \
    "https://www.pexels.com/download/video/$1/"
}

for row in "${clips[@]}"; do
  IFS='|' read -r name id variant <<<"$row"
  [ -f "videos/$name" ] && { echo "  have $name"; continue; }

  url=$(cdn_url "$id" "$variant" || true)
  if [ -z "$url" ]; then
    url=$(resolve "$id")
    [ -z "$url" ] && { echo "  !! could not resolve pexels $id"; continue; }
    echo "  !! $variant is gone for pexels $id; falling back to ${url##*/}"
    echo "     if that is not 1920x1080 the pixel constants will not line up"
  fi

  echo "  fetching $name (pexels $id)"
  curl -sSL --fail -o "videos/$name" "$url"
done

echo "done."
