# UkurPaket mockup v2: the courier's flow, step by step

Same layout as the first mockup (one 4K board per story: numbered phones, a title and caption under each, three
notes, a footer), now in AnterAja colours, magenta **#ED0677** and yellow **#FFCB08**, with plain business words:
no product or library names on the boards. The screens are the app's own renders (`../../ukur_paket_app`,
`ScreenshotTest`), so the mockup and APK v0.1 match screen for screen.

| File | |
|---|---|
| `alur_kurir.png` (3840 × 2160) | the main flow in 8 steps: Scan Resi → Persiapan → Scan Lantai → Pilih Paket → Scan Paket → Hasil Ukur → Berat → Tersimpan |
| `fitur_lapangan.png` (3840 × 2160) | field situations: Pilih Area, Paket berikutnya, arahan langsung, Perlu Dicek, Ukur di Hub, Data Ukur di Hub, Cek HP, Hari ini |
| `screens/01…17_*.png` (1348 × ±2860, transparent) | each screen in its phone frame, full size, for slides |
| `slide_ukur_mobileapp.md` | the 12-slide management deck for Claude Design: images, slide order, slide text, ready-to-paste prompt |

```bash
cd ../../ukur_paket_app && ./gradlew :app:testDebugUnitTest --tests '*ScreenshotTest*'   # renders the screens
cd - && python build_v2.py                                                                 # boards + screens/
```

The parcel photo is real with the shipping label blurred; the size on screen (27 × 15 × 6 cm) illustrates the flow,
it is not a measurement. The tracking numbers on screen (`TSA-901000001…`) are made up.
