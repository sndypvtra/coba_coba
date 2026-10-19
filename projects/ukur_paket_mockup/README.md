# UkurPaket: courier app mockup (measure L × W × H with the phone camera)

Mockup of the flow a courier follows to measure a parcel with method A (ARCore depth + floor detection),
made to test the flow with couriers before the app is built. Screen text is Indonesian.

| Screen | File | What the courier does |
|---|---|---|
| 1 | `screens/01_pilih_order.png` | picks the order or scans the label, so the size is tied to the tracking number |
| 2 | `screens/02_persiapan.png` | four picture rules (on the floor, one parcel, one step back, enough light), shown the first 3 times |
| 3 | `screens/03_cari_alas.png` | moves the phone sideways until white dots appear on the floor |
| 4 | `screens/04_pilih_paket.png` | aims the crosshair, or taps / draws a box; the parcels next to it are marked "Paket lain" |
| 5 | `screens/05_pindai.png` | sweeps the phone toward the parcel's corner for 2–3 s while depth dots fill in |
| 6 | `screens/06_hasil.png` | checks the 3D box drawn on the parcel and the size, then saves or repeats |
| 7 | `screens/07_berat.png` | types the scale weight; the app uses the larger of scale and volumetric weight (÷ 6.000) |
| 8 | `screens/08_tersimpan.png` | sees the saved record (photo, 3D box, size, time, GPS), sent when there is signal |
| 5b | `screens/05b_peringatan.png` | example warning: the parcel is cut off at the screen edge |
| 6b | `screens/06b_cek_ulang.png` | example of a doubtful result: shiny black plastic, Save locked for 2 s |

`screens/alur_kurir.png` (3840 × 2160) puts screens 1–8 on one board for a slide. `prototype/index.html` is
the clickable version: one self-contained file; the steps can be tapped as in the real app, and steps 3 and 5
run by themselves.

The camera screens use a real photo of a parcel (black plastic with a label and a FRAGILE sticker, two
cartons beside it). The shipping label is blurred in `assets.py`. The overlays are what the app would draw:
the floor grid, the parcel outline, the depth dots and the 3D box. The outline is found with plain OpenCV,
which is enough for a mockup. **The size on screen (27 × 15 × 6 cm) is an illustration for testing the flow,
not a measurement**: the footprint is scaled from the label (about 10 cm wide) and the height is a guess.
Names, addresses and tracking numbers are made up.

```bash
python assets.py <photo.jpg>   # blur the label, find the outline -> img/paket.jpg, img/geom.json
python build.py                # screens/*.png at 1236 x 2676, the board, prototype/index.html
python build.py --no-shot      # HTML only
```

Needs OpenCV and headless Chromium (`/opt/pw-browsers/...`, or set `CHROME=`). Type: Inter (SIL OFL 1.1, from
`../factory_mockup/assets/fonts`). Icons: Material Symbols Rounded (Apache 2.0), the subset in `fonts/`.
