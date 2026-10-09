"""Build assets/fonts/MaterialSymbolsRounded.ttf: only the icons the dashboards use.

    curl -L -o full.ttf "https://raw.githubusercontent.com/google/material-design-icons/master/variablefont/MaterialSymbolsRounded%5BFILL%2CGRAD%2Copsz%2Cwght%5D.ttf"
    python make_icon_font.py fonts/MaterialSymbolsRounded.ttf icons.txt   (run in this folder, with full.ttf here)

Filled, weight 500, optical size 24. Each icon is kept with the ligature that spells
its name, so `ui.Canvas.icon("inventory_2", ...)` draws it.
"""
import sys
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset
WANT = """inventory_2 conveyor_belt precision_manufacturing check_circle cancel error warning report history
play_arrow videocam videocam_off speed timer grid_view package_2 deployed_code block front_hand smart_toy
local_shipping bolt trending_up query_stats analytics schedule inventory fact_check rule
production_quantity_limits swap_horiz sync pause_circle notifications add_box verified grid_on
table_rows list_alt insights monitoring bar_chart scale sensors remove_circle do_not_disturb_on
package conveyor_belt keyboard_double_arrow_right arrow_forward call_split visibility hourglass_top
counter_1 numbers tag pin target radar filter_center_focus crop_free select_all view_module
location_on construction build handyman engineering low_priority priority_high donut_large pie_chart
stacked_bar_chart leaderboard straighten done_all task_alt new_releases unpublished
""".split()
f = TTFont('full.ttf')  # the full variable font, see the docstring
cmap = f.getBestCmap(); rev = {}
for cp, g in cmap.items(): rev.setdefault(g, cp)
lig = {}
for L in f['GSUB'].table.LookupList.Lookup:
    for st in L.SubTable:
        st = getattr(st, 'ExtSubTable', st)
        if hasattr(st, 'ligatures'):
            for first, ls in st.ligatures.items():
                for l in ls:
                    name = ''.join(f.getGlyphOrder() and [first] + l.Component)
                    lig[(first, tuple(l.Component))] = l.LigGlyph
# build name -> glyph by spelling
g2c = {g: chr(cp) for cp, g in cmap.items() if cp < 128}
names = {}
for (first, comps), out in lig.items():
    try:
        s = ''.join(g2c[x] for x in (first,) + comps)
    except KeyError:
        continue
    names[s] = out
have = [w for w in dict.fromkeys(WANT) if w in names]
print('missing:', [w for w in WANT if w not in names])
cps = [rev[names[w]] for w in have if names[w] in rev]
print(len(have), 'icons,', len(cps), 'with codepoints')
inst = instancer.instantiateVariableFont(f, {"FILL": 1, "GRAD": 0, "opsz": 24, "wght": 500})
opts = subset.Options(); opts.layout_features = ['liga', 'rlig', 'calt', 'ccmp']; opts.layout_closure = False
opts.name_IDs = ['*']; opts.notdef_outline = True
sub = subset.Subsetter(opts)
sub.populate(unicodes=cps + [ord(c) for c in 'abcdefghijklmnopqrstuvwxyz_0123456789 '])
sub.subset(inst)
inst.save(sys.argv[1])
open(sys.argv[2], 'w').write('\n'.join(have) + '\n')
