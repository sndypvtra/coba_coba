# Factory Vision: one web app per factory product

Each factory product is its own web app, with its own menu, screens and deck prompt, in the same look as the
warehouse mockup (`07_warehouse_live_ops/mockup`), so the decks can be shown alone or joined.

| App (folder in `apps/`) | PoC behind it | Pages | Deck prompt |
|---|---|---|---|
| `produce_grading` · tomato (USDA) and lemon (OECD) | `11_tomato_ripeness`, `12_lime_grading` | 7 | `produce_grading.md` |
| `fill_level_inspection` | `04_bottle_fill_volume` | 6 | `fill_level_inspection.md` |
| `pack_count_qc` · can trays and robot packing station | `08_pack_completeness` | 7 | `pack_count_qc.md` |
| `parcel_dimensioning` | `03_parcel_dimensioning` | 6 | `parcel_dimensioning.md` |

Every app tells the same story: Ringkasan → Live Monitoring → Dashboard TV → report or reject detail →
the product's own specification page → Kamera, Alert & Integrasi.

As in the warehouse mockup, every page is the product's own screen with its own analytics. From the PoC it
takes only the camera picture with the AI overlay drawn on it (exported clean by each dashboard script with
`--cam`, see `assets.py`), the snapshots, and every figure marked **PoC**. Screen text is Indonesian with the
common English terms of the plant floor. Plant names, people, daily totals and trends are illustrative, and
every page says so in its corner. No page shows a price.

```bash
python factory_mockup/assets.py           # camera pictures and snapshots -> img/
python factory_mockup/build.py            # every app -> apps/<app>/pages/*.png (3840 x 2160; --1x for 1920 x 1080)
python factory_mockup/build.py fill pack  # some apps
python factory_mockup/build.py --icons    # refetch the icon subset after using a new icon (network)
python factory_mockup/gen_md.py           # apps/<app>/<app>.md, the Claude Design prompt per app
```

Code: `build.py` (shell, per-app menus, web-app pages, the list of apps), `tv.py` (Dashboard TV pages),
`extra.py` (Live Monitoring, specification and settings pages added per app), `look.py` (styles and charts).
Needs headless Chromium (`/opt/pw-browsers/...`, or set `CHROME=`), OpenCV and the PoC outputs.
Type: Inter (SIL OFL 1.1). Icons: Material Symbols Rounded (Apache 2.0).
