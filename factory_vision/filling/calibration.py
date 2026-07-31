"""Every constant tied to this filling station.

These are the numbers that would need re-measuring if the camera moved, the
bottle changed, or the product colour changed. They are gathered here rather
than scattered through the code so the scope of a recalibration is one file.
``factory_vision.tools.perturbation_test`` measures what happens when they no
longer match the scene.
"""

from __future__ import annotations


# Front bottle, measured off the 1920x1080 frame: mouth y=490, inner base
# y=1020, body spans x=615..865.
# Right edge is 1010: the bottle body actually reaches x~1010 and the previous
# 900 clipped ~110 px of bore off it. Left stays tight at 618 because the bottle
# behind also holds product; nothing amber sits right of 1010, only background.
ROI = (618, 490, 1010, 1030)

# Bottom of the neck threads, read off the frame. This is the datum the stated
# capacity refers to - a filler's nominal volume is "up to the thread line", not
# "to the brim" and not "the fullest this clip happened to get". Using the
# fullest observed level made the last frame read 100% by construction, which is
# wrong: the liquid ends at y~700, some 115 px below the threads, so the bottle
# is visibly NOT full at the end of this clip.
THREAD_DATUM_Y = 585

# Template used to cancel the few px of camera shake, taken from the bottle's
# neck/shoulder which stays sharp and never fills with product.
TEMPLATE_FRAME = 140
TEMPLATE_BOX = (640, 520, 900, 640)

# Amber product. Calibrated from pixel statistics, not guessed:
#   liquid          H 15-20   S 105-255  V 162-207
#   conveyor        H 11-22   S   8-55   V 105-137
#   empty glass     H  6-20   S   8-60   V 111-175
# Absolute width that separates the falling jet from standing liquid. The jet
# runs 7-11 px; the shallowest pool is 80+. Used only to learn the bore, where a
# ratio test cannot be applied yet because the bore is what is being measured.
JET_MAX_WIDTH_PX = 40.0
# Rows whose learned bore falls below this fraction of the widest bore are
# treated as never observed. See bottle_profile for why.
BORE_MIN_FRACTION = 0.30

# Saturation is raised to 200 to reject product seen *through* glass. The front
# bottle's upper half is transparent and other filled bottles sit behind it, so
# their amber shows through and colour alone called it liquid inside this bottle.
# The extra glass layer desaturates it, and that is separable:
#   product, direct view          S 251-255
#   product seen through glass    S 104-199   <- was passing at S>=150
# At S>=150 the surface on the last frame read y=652; the real meniscus is y~690.
LIQUID_LO = (13, 200, 120)
LIQUID_HI = (30, 255, 255)

# Below the surface the region is liquid by definition, so a relaxed cut is used
# there purely to close the mask for display. The rods cast shadows that pull the
# product down to S 120-185, under the strict cut. This never moves the level:
# the surface is found with the strict cut, and volume integrates the bore.
LIQUID_LO_SHADOW = (13, 95, 90)

# Columns used to locate the surface: strictly inside the front bottle and right
# of where the neighbouring bottle's product is directly visible (it reaches
# x~690). Product in the bottle behind is just as saturated as product in this
# one, so colour cannot separate them - only position can.
SURFACE_BAND = (700, 890)

# Bottle silhouette, (y, x_left, x_right), read off the frame and interpolated
# between. The camera is fixed, so a hand-measured outline is exact and cheap.
# A rectangular ROI cannot express a bottle: it necessarily includes conveyor at
# the base corners, where product spilled on the belt was both shading the
# overlay outside the bottle and inflating the learned bore at the lowest rows.
BOTTLE_OUTLINE = [
    (585, 620, 1000),
    (650, 618, 1005),
    (700, 620, 1005),
    (800, 612, 1012),
    (900, 628, 1000),
    (960, 650, 975),
    (1010, 690, 935),
    (1029, 720, 900),
]


# A row only counts as standing liquid if the mask spans this much of the
# bottle's internal width there. The falling jet is ~3% wide; the pool is 50%+.
POOL_MIN_RATIO = 0.45
# Rows the mask may lose to specular highlights. Deliberately small: while the
# machine is filling there is a turbulent splash sheet 30-40 rows above the
# settled pool, separated from it by a narrow band. A tolerance large enough to
# bridge that band made the reading bistable, flipping between ~30% and ~50% on
# alternate frames (f161 30%, f162 49%). The settled pool is the fill level; the
# splash crest sits above it and overestimates. The static rod that crosses the
# bottle needs no bridging - it occludes every frame, so the learned bore
# profile already accounts for it and the ratio test self-calibrates.
POOL_GAP_TOLERANCE = 10
