# Factory Vision: mockup pages for the factory products

The web app and TV dashboard screens of the four factory products, rendered as 3840 × 2160 pictures (laid out at 1920 × 1080, rendered at 2×) for
the pitch deck. They use the same look as the warehouse mockup (`07_warehouse_live_ops/mockup`), so the
slides of the two decks join up. The deck prompt is in **`factory_mockup.md`**.

| Product | PoC behind it | Pages |
|---|---|---|
| Produce Grading (tomato · USDA, lemon · OECD) | `11_tomato_ripeness`, `12_lime_grading` | 02–07 |
| Fill Level Inspection | `04_bottle_fill_volume` | 08–10 |
| Pack Count QC (can trays, robot packing station) | `08_pack_completeness` | 11–14 |
| Parcel Dimensioning | `03_parcel_dimensioning` | 15–17 |
| Shared platform: product map, roles, alerts, cameras, plants, plans | – | 00–01, 18–21 |

Like the warehouse mockup, every page is the product's own screen with its own analytics (`build.py`, TV
dashboards in `tv.py`). From the PoC it takes only the camera picture with the AI overlay drawn on it, exported
clean by each dashboard script with `--cam` (see `assets.py`), the snapshots, and every figure marked **PoC**.
Screen text is Indonesian with the common English terms of the plant floor (line, reject, lot, SKU, QC).
Plant names, people, daily totals and trends are illustrative, and every page says so in its corner.
No page shows a price.

```bash
python factory_mockup/assets.py         # pictures from the PoC videos -> img/
python factory_mockup/build.py          # every page -> html/ and pages/ (3840 x 2160; --1x for 1920 x 1080)
python factory_mockup/build.py 04 09    # some pages
python factory_mockup/build.py --icons  # refetch the icon subset after using a new icon (network)
```

Needs headless Chromium (`/opt/pw-browsers/...`, or set `CHROME=`), OpenCV and the PoC videos.
Type: Inter (SIL OFL 1.1). Icons: Material Symbols Rounded (Apache 2.0).
