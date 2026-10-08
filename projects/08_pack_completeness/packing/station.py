"""A packing station, built in Blender: a Cartesian robot places products into boxes of 20.

Seen from one fixed camera above the line. Products ride a feeder belt (top of
the frame) to a stop; the robot head picks each one and sets it into the next of
the 20 slots (5 x 4) of an open shipping box on the main conveyor (bottom). A
full box leaves to the right while the next comes in.

The second box comes out two short: the feeder has two gaps, the head still
makes those trips, and two slots stay empty. Everything the analytics will be
judged on is fixed here, in PLAN, before anything is rendered.
"""
from __future__ import annotations

import math
import os
import random
import sys
from dataclasses import dataclass, field

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scene import (_node, _obj_from_bmesh, mat_cardboard, mat_floor,  # noqa: E402
                   mat_plain, mat_steel)

FPS = 25
CYCLE = 16                     # frames per pick-and-place: 0.64 s, about 94 picks a minute
COLS, ROWS = 5, 4
EXPECTED = COLS * ROWS         # 20
PITCH = 0.10
ITEM = (0.088, 0.088, 0.07)    # product carton, w x d x h (m); sits below the box rim
BOX_IN = (COLS * PITCH + 0.004, ROWS * PITCH + 0.004)
BOX_H = 0.10
WALL = 0.005
BOX_Y = -0.16                  # main conveyor centre line
PICK = (0.0, 0.40)             # feeder stop, where the head picks
FEED_SPEED = 0.30              # m/s, so one product arrives per cycle at 0.12 m spacing
EXCHANGE = 40                  # frames to swap a full box for an empty one
TRAVEL = 1.00                  # box spacing on the main conveyor
SEED = 11

# Box plan, in the order the boxes reach the station. `start` is how many are
# already in when the clip opens; `gaps` are feeder gaps, by cycle index, that
# leave a slot empty.
PLAN = [
    {"start": 14, "gaps": []},
    {"start": 0, "gaps": [6, 14]},
    {"start": 0, "gaps": []},
]


@dataclass
class Box:
    idx: int
    obj: bpy.types.Object
    placed: list = field(default_factory=list)   # (frame, slot)
    empty_slots: list = field(default_factory=list)


def slot_xy(slot):
    """Slot 0 is back-left (far from the camera); numbering runs left to right, then forward."""
    r, c = divmod(slot, COLS)
    x = (c - (COLS - 1) / 2) * PITCH
    y = ((ROWS - 1) / 2 - r) * PITCH
    return x, y


# ---- materials ---------------------------------------------------------------
def mat_product():
    """White carton, blue band round the sides, blue panel with a white border on top."""
    m = bpy.data.materials.new("product")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.45
    tex = _node(nt, "ShaderNodeTexCoord", (-1100, 0))
    xyz = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tex.outputs["Object"], xyz.inputs["Vector"])

    def cmp(op, a, val):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        nt.links.new(a, n.inputs[0])
        n.inputs[1].default_value = val
        return n.outputs[0]

    def mul(a, c):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = "MULTIPLY"
        nt.links.new(a, n.inputs[0])
        nt.links.new(c, n.inputs[1])
        return n.outputs[0]

    def mx(a, c):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = "MAXIMUM"
        nt.links.new(a, n.inputs[0])
        nt.links.new(c, n.inputs[1])
        return n.outputs[0]

    ax = nt.nodes.new("ShaderNodeMath")
    ax.operation = "ABSOLUTE"
    nt.links.new(xyz.outputs["X"], ax.inputs[0])
    ay = nt.nodes.new("ShaderNodeMath")
    ay.operation = "ABSOLUTE"
    nt.links.new(xyz.outputs["Y"], ay.inputs[0])
    top = cmp("GREATER_THAN", xyz.outputs["Z"], ITEM[2] - 0.002)
    inner = mul(cmp("LESS_THAN", ax.outputs[0], 0.030), cmp("LESS_THAN", ay.outputs[0], 0.030))
    band = mul(cmp("GREATER_THAN", xyz.outputs["Z"], 0.022), cmp("LESS_THAN", xyz.outputs["Z"], 0.046))
    blue = mx(mul(top, inner), band)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0.86, 0.86, 0.84, 1)
    mix.inputs["B"].default_value = (0.05, 0.22, 0.62, 1)
    nt.links.new(blue, mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def mat_belt_keyed(name, keys):
    """Dark belt whose surface scrolls by `keys` [(frame, offset_x)]."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.7
    tex = _node(nt, "ShaderNodeTexCoord", (-1000, 0))
    mp = nt.nodes.new("ShaderNodeMapping")
    nt.links.new(tex.outputs["Object"], mp.inputs["Vector"])
    loc = mp.inputs["Location"]
    for f, off in keys:
        loc.default_value = (-off, 0, 0)
        loc.keyframe_insert("default_value", frame=f)
    noise = _node(nt, "ShaderNodeTexNoise", (-600, 150), Scale=5.0, Detail=3.0)
    nt.links.new(mp.outputs["Vector"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (0.03, 0.032, 0.035, 1)
    ramp.color_ramp.elements[1].color = (0.075, 0.075, 0.078, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    fine = _node(nt, "ShaderNodeTexNoise", (-600, -100), Scale=220.0, Detail=4.0)
    nt.links.new(mp.outputs["Vector"], fine.inputs["Vector"])
    bump = _node(nt, "ShaderNodeBump", (-300, -100), Strength=0.04)
    nt.links.new(fine.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


# ---- geometry ----------------------------------------------------------------
def cube(name, size, loc, mat, bevel=0.0):
    bm = bmesh.new()
    v = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, verts=v, vec=size)
    bmesh.ops.translate(bm, verts=v, vec=loc)
    ob = _obj_from_bmesh(name, bm, mat)
    for p in ob.data.polygons:
        p.use_smooth = False
    if bevel:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return ob


def cylinder(name, r, h, loc, mat, axis="Z", seg=24):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=h)
    if axis != "Z":
        from mathutils import Matrix
        rot = Matrix.Rotation(math.pi / 2, 3, "Y" if axis == "X" else "X")
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=rot)
    bmesh.ops.translate(bm, verts=bm.verts, vec=loc)
    return _obj_from_bmesh(name, bm, mat)


def make_box(name, mat):
    lx, ly = BOX_IN[0] + 2 * WALL, BOX_IN[1] + 2 * WALL
    bm = bmesh.new()

    def part(cx, cy, cz, sx, sy, sz):
        v = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        bmesh.ops.scale(bm, verts=v, vec=(sx, sy, sz))
        bmesh.ops.translate(bm, verts=v, vec=(cx, cy, cz))

    part(0, 0, WALL / 2, lx, ly, WALL)
    part(0, ly / 2 - WALL / 2, BOX_H / 2, lx, WALL, BOX_H)
    part(0, -ly / 2 + WALL / 2, BOX_H / 2, lx, WALL, BOX_H)
    part(lx / 2 - WALL / 2, 0, BOX_H / 2, WALL, ly - 2 * WALL, BOX_H)
    part(-lx / 2 + WALL / 2, 0, BOX_H / 2, WALL, ly - 2 * WALL, BOX_H)
    # open flaps folded outwards on the long sides
    part(0, ly / 2 + 0.045, BOX_H - 0.002, lx, 0.09, 0.004)
    part(0, -ly / 2 - 0.045, BOX_H - 0.002, lx, 0.09, 0.004)
    ob = _obj_from_bmesh(name, bm, mat)
    for p in ob.data.polygons:
        p.use_smooth = False
    mod = ob.modifiers.new("bevel", "BEVEL")
    mod.width = 0.0015
    mod.segments = 2
    return ob


def make_item_mesh(mat):
    bm = bmesh.new()
    v = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, verts=v, vec=ITEM)
    bmesh.ops.translate(bm, verts=v, vec=(0, 0, ITEM[2] / 2))
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.003, segments=2, affect="EDGES")
    me = bpy.data.meshes.new("product")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    return me


# ---- timeline ----------------------------------------------------------------
# One pick-and-place, as (frame offset, where, height) waypoints for the head.
# The product is gripped from GRIP to RELEASE and rides under the head then.
GRIP, RELEASE = 3, 11
Z_UP = ITEM[2] + 0.13          # carried product clears the box walls and the rows inside
Z_PICK = ITEM[2] + 0.002
Z_PLACE = ITEM[2] + WALL + 0.001
WAYPOINTS = [(0, "pick", "up"), (2, "pick", "pick"), (GRIP, "pick", "pick"), (5, "pick", "up"),
             (9, "slot", "up"), (RELEASE - 0.001, "slot", "place"), (12, "slot", "place"),
             (13, "slot", "up")]


def timeline():
    """Frame numbers for every box move and every pick, from PLAN."""
    f = 1
    stations, cycles = [], []
    for bi, plan in enumerate(PLAN):
        if bi > 0:
            f += EXCHANGE
        t_in = f
        slots = list(range(plan["start"], EXPECTED))
        for ci, slot in enumerate(slots):
            cycles.append({"box": bi, "slot": slot, "start": f + ci * CYCLE,
                           "release": f + ci * CYCLE + RELEASE,
                           "empty": ci in plan["gaps"]})
        f += len(slots) * CYCLE
        stations.append((t_in, f))          # box bi sits at the station [t_in, f]
    end = f + EXCHANGE
    return stations, cycles, end


def exchanges(stations, end):
    """(start, stop) of every belt move: before each later box, and the last box leaving."""
    return [(st[0] - EXCHANGE, st[0]) for st in stations[1:]] + [(end - EXCHANGE, end)]


def belt_travel(stations, end, f):
    """How far the main belt has moved by frame f (m)."""
    d = 0.0
    for a, b in exchanges(stations, end):
        if f >= b:
            d += TRAVEL
        elif f > a:
            u = (f - a) / EXCHANGE
            d += TRAVEL * u * u * (3 - 2 * u)      # belt eases in and out
    return d


def box_x(stations, end, bi, f):
    """Boxes queue TRAVEL apart and all move with the belt."""
    return -bi * TRAVEL + belt_travel(stations, end, f)


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * u * (u * (6 * u - 15) + 10)


def head_path(cycles):
    """Head position at every frame, from the waypoints of every cycle (smootherstep between)."""
    z = {"up": Z_UP, "pick": Z_PICK, "place": Z_PLACE}
    pts = []
    for c in cycles:
        sx, sy = slot_xy(c["slot"])
        where = {"pick": PICK, "slot": (sx, BOX_Y + sy)}
        for off, w, h in WAYPOINTS:
            pts.append((c["start"] + off, (*where[w], z[h])))
    pts.sort()

    def at(f):
        if f <= pts[0][0]:
            return Vector(pts[0][1])
        for (fa, pa), (fb, pb) in zip(pts, pts[1:]):
            if fa <= f <= fb:
                u = ease((f - fa) / (fb - fa)) if fb > fa else 1.0
                return Vector(pa).lerp(Vector(pb), u)
        return Vector((*PICK, Z_UP))
    return at


def key_linear(ob, path, frame, value):
    setattr(ob, path, value)
    ob.keyframe_insert(path, frame=frame)


def set_interp(ob, kind="LINEAR"):
    if ob.animation_data and ob.animation_data.action:
        for fc in ob.animation_data.action.fcurves:
            for k in fc.keyframe_points:
                k.interpolation = kind


def build(seed=SEED):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rng = random.Random(seed)
    sc = bpy.context.scene
    sc.render.fps = FPS
    stations, cycles, end = timeline()
    sc.frame_start, sc.frame_end = 1, end

    steel, card = mat_steel(), mat_cardboard()
    dark = mat_plain("dark", (0.05, 0.05, 0.055), 0.5)
    rubber = mat_plain("rubber", (0.02, 0.02, 0.02), 0.6)
    yellow = mat_plain("yellow", (0.75, 0.52, 0.02), 0.45)
    product = mat_product()
    item_mesh = make_item_mesh(product)

    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, -0.8))
    _obj_from_bmesh("floor", bm, mat_floor())

    # main conveyor: the belt surface moves exactly as the boxes on it do
    keys = sorted({1, end} | {t for ab in exchanges(stations, end) for t in range(ab[0], ab[1] + 1)})
    belt_main = mat_belt_keyed("belt_main", [(f, belt_travel(stations, end, f)) for f in keys])
    cube("belt_main", (4.0, 0.62, 0.01), (0, BOX_Y, -0.005), belt_main)
    for s in (-1, 1):
        cube(f"frame_main_{s}", (4.0, 0.04, 0.08), (0, BOX_Y + s * 0.33, -0.02), steel, 0.003)
    # feeder belt: runs all the time
    belt_feed = mat_belt_keyed("belt_feed", [(1, 0.0), (end, FEED_SPEED * end / FPS)])
    cube("belt_feed", (4.0, 0.14, 0.01), (-1.9, PICK[1], -0.005), belt_feed)
    for s in (-1, 1):
        cube(f"rail_feed_{s}", (2.0, 0.012, 0.05), (-1.0 + 0.02, PICK[1] + s * 0.062, 0.03), steel, 0.002)
    cube("stop_feed", (0.012, 0.13, 0.06), (PICK[0] + ITEM[0] / 2 + 0.008, PICK[1], 0.03), yellow, 0.002)
    cube("stopline", (0.01, 0.62, 0.002), (BOX_IN[0] / 2 + 0.03, BOX_Y, 0.0012), yellow)

    # cantilever Cartesian robot reaching in from behind: an x rail on two posts,
    # a carriage on it, a slim y arm through the carriage, a z slide at the arm tip
    RAIL_Y, RAIL_Z = 0.62, 0.42
    cube("x_rail", (1.3, 0.08, 0.07), (0, RAIL_Y, RAIL_Z), steel, 0.004)
    for x in (-0.62, 0.62):
        cube(f"x_post_{x}", (0.06, 0.06, 1.24), (x, RAIL_Y, RAIL_Z - 0.035 - 0.62), steel, 0.004)
    carriage = cube("carriage", (0.13, 0.14, 0.09), (0, 0, 0), dark, 0.008)
    arm = cube("y_arm", (0.05, 0.95, 0.045), (0, 0.475 - 0.03, 0), steel, 0.004)
    slide = cube("z_slide", (0.07, 0.05, 0.10), (0, 0, 0), dark, 0.006)
    rod = cube("z_rod", (0.022, 0.022, 0.42), (0, 0, 0.21), steel, 0.003)
    head = cylinder("head", 0.04, 0.03, (0, 0, 0.015), dark, seg=32)
    for i, (dx, dy) in enumerate([(-0.022, -0.022), (0.022, -0.022), (-0.022, 0.022), (0.022, 0.022)]):
        cup = cylinder(f"cup_{i}", 0.011, 0.012, (dx, dy, -0.006), rubber, seg=16)
        cup.parent = head
    rod.parent = head
    ARM_Z = RAIL_Z + 0.09

    at = head_path(cycles)
    for f in range(1, end + 1):
        p = at(f)
        head.location = p
        head.keyframe_insert("location", frame=f)
        carriage.location = (p.x, RAIL_Y, RAIL_Z + 0.075)
        carriage.keyframe_insert("location", frame=f)
        arm.location = (p.x, p.y, ARM_Z)
        arm.keyframe_insert("location", frame=f)
        slide.location = (p.x, p.y - 0.05, ARM_Z)
        slide.keyframe_insert("location", frame=f)
    for ob in (head, carriage, arm, slide):
        set_interp(ob)

    def with_box(bi, f, x, y):
        return Vector((x + box_x(stations, end, bi, f), BOX_Y + y, WALL))

    belt_keys = sorted({t for ab in exchanges(stations, end) for t in range(ab[0], ab[1] + 1, 2)} | {end})

    boxes = []
    for bi, plan in enumerate(PLAN):
        ob = make_box(f"box_{bi}", card)
        boxes.append(Box(bi, ob))
        for f in sorted({1} | set(belt_keys)):
            key_linear(ob, "location", f, Vector((box_x(stations, end, bi, f), BOX_Y, 0.0)))
        set_interp(ob)
        for slot in range(plan["start"]):
            sx, sy = slot_xy(slot)
            it = bpy.data.objects.new(f"item_{bi}_{slot}", item_mesh)
            sc.collection.objects.link(it)
            it.parent = ob
            it.location = (sx + rng.uniform(-0.003, 0.003), sy + rng.uniform(-0.003, 0.003), WALL)
            it.rotation_euler = (0, 0, math.radians(rng.uniform(-2, 2)))
            boxes[bi].placed.append((1, slot))

    feed_frames = int(round(1.7 / FEED_SPEED * FPS))      # feeder run in view before the stop
    for c in cycles:
        s, bi, slot = c["start"], c["box"], c["slot"]
        if c["empty"]:
            boxes[bi].empty_slots.append(slot)
            continue
        sx, sy = slot_xy(slot)
        jx, jy, jr = rng.uniform(-0.003, 0.003), rng.uniform(-0.003, 0.003), rng.uniform(-2, 2)
        it = bpy.data.objects.new(f"item_{bi}_{slot}", item_mesh)
        sc.collection.objects.link(it)
        # ride the feeder up to the stop
        t0 = s - feed_frames
        for f in (max(1, t0), s):
            key_linear(it, "location", f, Vector((PICK[0] - FEED_SPEED * (s - f) / FPS, PICK[1], 0.0)))
        # under the head from grip to release
        for f in range(s + GRIP, s + RELEASE + 1):
            p = at(f)
            key_linear(it, "location", f, Vector((p.x, p.y, p.z - Z_PICK)))
        # then in its box, moving with it
        for f in [s + RELEASE + 1] + [t for t in belt_keys if t > s + RELEASE + 1]:
            key_linear(it, "location", f, with_box(bi, f, sx + jx, sy + jy))
        it.rotation_euler = (0, 0, math.radians(jr))
        set_interp(it)
        boxes[bi].placed.append((s + RELEASE, slot))
        if t0 > 1:
            it.hide_render = True
            it.keyframe_insert("hide_render", frame=1)
            it.hide_render = False
            it.keyframe_insert("hide_render", frame=t0)
            for fc in it.animation_data.action.fcurves:
                if fc.data_path == "hide_render":
                    for k in fc.keyframe_points:
                        k.interpolation = "CONSTANT"

    cam = build_lights_and_camera()
    return boxes, cycles, stations, cam


def build_lights_and_camera():
    sc = bpy.context.scene
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.5, 0.52, 0.55, 1)
    bg.inputs["Strength"].default_value = 0.08
    sc.world = world
    for name, loc, size, power in [("key", (0.6, -0.9, 2.3), 1.4, 150),
                                   ("fill", (-1.0, 0.9, 2.1), 1.4, 70),
                                   ("top", (0.0, 0.1, 2.0), 0.6, 60)]:
        ld = bpy.data.lights.new(name, "AREA")
        ld.size = size
        ld.energy = power
        ld.color = (1.0, 0.97, 0.93)
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        lo.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(lo)
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = 30
    cam = bpy.data.objects.new("cam", cam_d)
    cam.location = (0.0, -1.05, 1.95)
    target = Vector((0.0, 0.08, 0.0))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam
