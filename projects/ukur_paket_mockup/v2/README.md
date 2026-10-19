# UkurPaket mockup v2: the courier's flow, step by step

The screens here are the app's own renders (`../../ukur_paket_app`, `ScreenshotTest`), so the mockup and APK v0.1
match screen for screen. Colours follow AnterAja: magenta **#ED0677** (buttons on anteraja.id and in the logo) and
yellow **#FFCB08** (the logo). Green / orange / red stay for status only (Akurat / Perlu Dicek / error). The app's name
stays UkurPaket; no AnterAja logo is used. Screen text is Indonesian, with the common field terms agreed for v0.1.

`alur_kurir.jpg` (3840 × 3132): the main flow. `kondisi_khusus.jpg` (3840 × 1746): the exceptions.
`screens/` holds each screen at full size (1236 × 2676, JPEG), numbered as on the boards.

## Main flow

| # | Screen | What the courier does |
|---|---|---|
| 1 | Cek Perangkat | Opens the app once; it checks ARCore and Depth and shows the mode (AR + Depth / AR Standar / Tidak Didukung). |
| 2 | Pickup | Picks a tracking number from today's list, or taps **Scan resi** (or **Ketik Resi**). |
| 3 | Persiapan | Reads 4 rules (on the floor, one parcel with ±5 cm space, one step back, enough light). Shown the first 3 times. |
| 4 | Scan Lantai | Moves the phone sideways until white dots cover the floor. |
| 5 | Pilih Paket | Taps the parcel. It gets a magenta outline and **Paket dipilih**; other parcels show **Paket lain**. |
| 6 | Pilih Area | Only if a tap picks part of the parcel: **Pilih Area**, then drag a box around it. |
| 7 | Scan Paket | **Mulai Scan**, then moves the phone slowly round the parcel's corner until the ring reaches 100 %. |
| 8 | Hasil Ukur | Checks the 3D box and the size (L × W × H, volume, volumetric weight), then **Simpan**. |
| 9 | Berat | Types the **Berat Aktual** from the scale (optional); **Berat Tagih** = the larger of actual and volumetric. |
| 10 | Tersimpan | The record: photo with the 3D box, size, weight, time, GPS. **Paket berikutnya** or **Selesai pickup**. |
| 11 | Paket Berikutnya | No new floor scan; parcels already measured carry a ✓ and their tracking number. |
| 12 | Riwayat | Every record on the phone, shareable as JSON. |

## Special cases

| | Screen | When |
|---|---|---|
| A | Peringatan | The parcel is cut off at the screen edge, the phone moves too fast, it is too dark (flashlight button top right). |
| B | Perlu Dicek | Low score: orange box, **Simpan** locked for 2 s; repeat from another angle. |
| C | Ukur di Hub | After 2 failed attempts: **Gagal ukur? Ukur di Hub**, pick a reason. |
| D | Data Ukur di Hub | The record keeps photo, time, location and reason; the hub measures the size. |
| E | HP Tidak Didukung | A phone without ARCore is detected on the first screen. |
| F | Tanpa ARCore | The parcel is still picked up and marked **Ukur di Hub**. |

```bash
cd ../../ukur_paket_app && ./gradlew :app:testDebugUnitTest --tests '*ScreenshotTest*'   # renders the screens
cd - && python build_v2.py                                                                 # boards + screens/
```
