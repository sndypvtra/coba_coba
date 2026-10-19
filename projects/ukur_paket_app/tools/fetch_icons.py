"""Download the Material Symbols Rounded subset the app draws (Apache 2.0), outline and filled.

    python tools/fetch_icons.py      # -> app/src/main/res/font/msym_line.ttf, msym_fill.ttf
"""
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "app" / "src" / "main" / "res" / "font"
NAMES = sorted(set("""signal_cellular_alt wifi battery_full arrow_back more_vert barcode_scanner inventory_2 check_circle schedule
chevron_right location_on local_shipping cloud_done cloud_upload history person crop_free directions_walk light_mode photo_camera
swipe lock crop view_in_ar straighten scale bluetooth warning refresh check done_all front_hand info arrow_forward close
flashlight_on flashlight_off deployed_code package_2 home storefront pin_drop timer gps_fixed touch_app open_with sync qr_code_2
settings share delete edit_note keyboard add search smartphone error tune folder_zip download fiber_manual_record
radio_button_checked expand_more task_alt help warehouse highlight_alt location_off""".split()))

for fill, fn in ((0, "msym_line.ttf"), (1, "msym_fill.ttf")):
    url = ("https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,"
           f"{fill},0&icon_names={','.join(NAMES)}&display=block")
    css = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Wget/1.21"}), timeout=60).read().decode()
    f = css.split("url(")[1].split(")")[0]
    data = urllib.request.urlopen(urllib.request.Request(f, headers={"User-Agent": "Wget/1.21"}), timeout=60).read()
    (OUT / fn).write_bytes(data)
    print(fn, len(NAMES), "icons", len(data) // 1024, "KB")
