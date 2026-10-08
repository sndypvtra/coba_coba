"""Build the conveyor scene in Blender: trays of ten cans, some packed one short.

Run through render.py, which imports this module inside Blender's Python (the
`bpy` wheel from PyPI is enough - no Blender install, no GPU).

Everything the analytics will later be judged against is decided here, in
LINE: which tray is short and which of its ten slots is empty. render.py writes
that out per frame as ground truth, so a count the AI reports can be checked
against what was actually built rather than against someone's eye.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import bmesh
import bpy
from mathutils import Matrix, Vector

# ---- the line --------------------------------------------------------------
FPS = 30
SECONDS = 15
SPEED = 0.30                 # belt speed, m/s
COLS, ROWS = 5, 2            # cans per tray: 5 along the belt, 2 across
EXPECTED = COLS * ROWS       # 10

CAN_R, CAN_H = 0.033, 0.115
PITCH = 0.072                # can centre spacing inside the tray
TRAY_L = COLS * PITCH + 0.016
TRAY_W = ROWS * PITCH + 0.016
TRAY_H = 0.055
TRAY_GAP = 0.26              # belt between trays

# Tray order as it enters the camera. A number is the count packed; the empty
# slot of a short tray is picked by the seeded RNG so it is not always the same
# corner. Two short trays in twelve is a far higher defect rate than any real
# line, which is the point: the clip has to show the event more than once.
LINE = [10, 10, 10, 9, 10, 9, 10, 10, 9, 10, 10, 10]
SEED = 7

BELT_W = 0.30
BELT_LEN = 9.0


@dataclass
class Tray:
    idx: int
    obj: bpy.types.Object
    packed: int
    missing: list[int]       # slot numbers 0..9, row-major from the leading edge
    x0: float                # x at frame 1


# ---- materials -------------------------------------------------------------
def _node(nt, kind, loc=(0, 0), **inputs):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def mat_cardboard():
    m = bpy.data.materials.new("cardboard")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = _node(nt, "ShaderNodeTexCoord", (-900, 0))
    noise = _node(nt, "ShaderNodeTexNoise", (-700, 100), Scale=60.0, Detail=6.0)
    nt.links.new(tex.outputs["Object"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-450, 100)
    ramp.color_ramp.elements[0].color = (0.42, 0.27, 0.14, 1)
    ramp.color_ramp.elements[1].color = (0.58, 0.41, 0.24, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.85
    # faint corrugation ridges
    wave = _node(nt, "ShaderNodeTexWave", (-700, -200), Scale=180.0, Distortion=0.6)
    nt.links.new(tex.outputs["Object"], wave.inputs["Vector"])
    bump = _node(nt, "ShaderNodeBump", (-300, -200), Strength=0.08)
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def mat_can():
    """Aluminium top and bottom, printed label between, from object Z."""
    m = bpy.data.materials.new("can")
    m.use_nodes = True
    nt = m.node_tree
    out = nt.nodes["Material Output"]
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    metal = _node(nt, "ShaderNodeBsdfPrincipled", (-200, 300),
                  Metallic=1.0, Roughness=0.34)
    metal.inputs["Base Color"].default_value = (0.66, 0.67, 0.69, 1)
    label = _node(nt, "ShaderNodeBsdfPrincipled", (-200, -100), Roughness=0.32)
    label.inputs["Coat Weight"].default_value = 0.6
    # red body with a white band, a plain beverage label
    tex = _node(nt, "ShaderNodeTexCoord", (-1000, 0))
    xyz = nt.nodes.new("ShaderNodeSeparateXYZ")
    xyz.location = (-800, 0)
    nt.links.new(tex.outputs["Object"], xyz.inputs["Vector"])
    mixc = nt.nodes.new("ShaderNodeMix")
    mixc.data_type = "RGBA"
    mixc.location = (-400, -150)
    mixc.inputs["A"].default_value = (0.62, 0.03, 0.04, 1)
    mixc.inputs["B"].default_value = (0.93, 0.92, 0.88, 1)
    # white band where 55 mm < z < 75 mm
    lo = nt.nodes.new("ShaderNodeMath")
    lo.operation = "GREATER_THAN"
    lo.inputs[1].default_value = 0.055
    lo.location = (-600, -300)
    hi = nt.nodes.new("ShaderNodeMath")
    hi.operation = "LESS_THAN"
    hi.inputs[1].default_value = 0.075
    hi.location = (-600, -420)
    both = nt.nodes.new("ShaderNodeMath")
    both.operation = "MULTIPLY"
    both.location = (-450, -350)
    nt.links.new(xyz.outputs["Z"], lo.inputs[0])
    nt.links.new(xyz.outputs["Z"], hi.inputs[0])
    nt.links.new(lo.outputs[0], both.inputs[0])
    nt.links.new(hi.outputs[0], both.inputs[1])
    nt.links.new(both.outputs[0], mixc.inputs["Factor"])
    nt.links.new(mixc.outputs["Result"], label.inputs["Base Color"])
    # metal where z < 8 mm or z > h - 10 mm
    bot = nt.nodes.new("ShaderNodeMath")
    bot.operation = "LESS_THAN"
    bot.inputs[1].default_value = 0.008
    bot.location = (-600, 300)
    top = nt.nodes.new("ShaderNodeMath")
    top.operation = "GREATER_THAN"
    top.inputs[1].default_value = CAN_H - 0.010
    top.location = (-600, 180)
    either = nt.nodes.new("ShaderNodeMath")
    either.operation = "MAXIMUM"
    either.location = (-450, 240)
    nt.links.new(xyz.outputs["Z"], bot.inputs[0])
    nt.links.new(xyz.outputs["Z"], top.inputs[0])
    nt.links.new(bot.outputs[0], either.inputs[0])
    nt.links.new(top.outputs[0], either.inputs[1])
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.location = (100, 0)
    nt.links.new(either.outputs[0], mix.inputs["Fac"])
    nt.links.new(label.outputs["BSDF"], mix.inputs[1])
    nt.links.new(metal.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return m


def mat_belt():
    m = bpy.data.materials.new("belt")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.035, 0.037, 0.04, 1)
    bsdf.inputs["Roughness"].default_value = 0.7
    tex = _node(nt, "ShaderNodeTexCoord", (-1000, 0))
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.location = (-800, 0)
    nt.links.new(tex.outputs["Object"], mapping.inputs["Vector"])
    # the belt surface scrolls with the trays, so wear marks move with them
    loc = mapping.inputs["Location"]
    loc.default_value = (0, 0, 0)
    loc.keyframe_insert("default_value", frame=1)
    loc.default_value = (-SPEED * SECONDS, 0, 0)
    loc.keyframe_insert("default_value", frame=1 + FPS * SECONDS)
    noise = _node(nt, "ShaderNodeTexNoise", (-600, -100), Scale=220.0, Detail=4.0)
    nt.links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    bump = _node(nt, "ShaderNodeBump", (-300, -100), Strength=0.04)
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    scuff = _node(nt, "ShaderNodeTexNoise", (-600, 150), Scale=4.0, Detail=3.0)
    nt.links.new(mapping.outputs["Vector"], scuff.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-400, 150)
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (0.03, 0.032, 0.035, 1)
    ramp.color_ramp.elements[1].color = (0.075, 0.075, 0.078, 1)
    nt.links.new(scuff.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def mat_steel():
    m = bpy.data.materials.new("steel")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.62, 0.63, 0.65, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = 0.38
    b.inputs["Anisotropic"].default_value = 0.6
    return m


def mat_plain(name, rgb, rough=0.8):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def mat_floor():
    m = bpy.data.materials.new("floor")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    noise = _node(nt, "ShaderNodeTexNoise", (-600, 0), Scale=12.0, Detail=10.0)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-350, 0)
    ramp.color_ramp.elements[0].color = (0.18, 0.19, 0.19, 1)
    ramp.color_ramp.elements[1].color = (0.30, 0.30, 0.29, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.6
    return m


# ---- geometry --------------------------------------------------------------
def _obj_from_bmesh(name, bm, mat):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def make_can_mesh(mat):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=CAN_R,
                          radius2=CAN_R, depth=CAN_H)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, CAN_H / 2))
    # recessed lid: inset the top cap and push it down so the rim catches light
    top = [f for f in bm.faces if f.normal.z > 0.9]
    r = bmesh.ops.inset_region(bm, faces=top, thickness=0.004, depth=0)
    bmesh.ops.translate(bm, verts=list({v for f in top for v in f.verts}),
                        vec=(0, 0, -0.004))
    del r
    me = bpy.data.meshes.new("can")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = abs(p.normal.z) < 0.5
    return me


def make_tray(name, mat):
    """Open-top cardboard tray with 4 mm walls."""
    bm = bmesh.new()
    t = 0.004
    hl, hw = TRAY_L / 2, TRAY_W / 2

    def box(cx, cy, cz, sx, sy, sz):
        geom = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        bmesh.ops.scale(bm, verts=geom, vec=(sx, sy, sz))
        bmesh.ops.translate(bm, verts=geom, vec=(cx, cy, cz))

    box(0, 0, t / 2, TRAY_L, TRAY_W, t)                       # floor
    box(0, hw - t / 2, TRAY_H / 2, TRAY_L, t, TRAY_H)         # long walls
    box(0, -hw + t / 2, TRAY_H / 2, TRAY_L, t, TRAY_H)
    box(hl - t / 2, 0, TRAY_H / 2, t, TRAY_W - 2 * t, TRAY_H)  # short walls
    box(-hl + t / 2, 0, TRAY_H / 2, t, TRAY_W - 2 * t, TRAY_H)
    ob = _obj_from_bmesh(name, bm, mat)
    for p in ob.data.polygons:
        p.use_smooth = False
    bev = ob.modifiers.new("bevel", "BEVEL")
    bev.width = 0.0012
    bev.segments = 2
    return ob


def slot_xy(slot):
    """Slot 0 is front-left (leading edge, +x); numbering runs across, then back."""
    col, row = divmod(slot, ROWS)
    x = (COLS - 1) / 2 * PITCH - col * PITCH
    y = (row - (ROWS - 1) / 2) * PITCH
    return x, y


def build_line(rng):
    cardboard, can_mat = mat_cardboard(), mat_can()
    can_mesh = make_can_mesh(can_mat)
    trays = []
    x = 1.25                      # first tray already in view near the right edge
    for i, packed in enumerate(LINE):
        tray = make_tray(f"tray_{i:02d}", cardboard)
        tray.location = (x, rng.uniform(-0.006, 0.006), 0.0)
        tray.rotation_euler = (0, 0, math.radians(rng.uniform(-1.2, 1.2)))
        missing = sorted(rng.sample(range(EXPECTED), EXPECTED - packed))
        for s in range(EXPECTED):
            if s in missing:
                continue
            cx, cy = slot_xy(s)
            can = bpy.data.objects.new(f"can_{i:02d}_{s}", can_mesh)
            bpy.context.collection.objects.link(can)
            can.parent = tray
            can.location = (cx + rng.uniform(-0.0015, 0.0015),
                            cy + rng.uniform(-0.0015, 0.0015), 0.004)
            can.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi))
        trays.append(Tray(i, tray, packed, missing, x))
        x -= TRAY_L + TRAY_GAP + rng.uniform(-0.02, 0.05)
    return trays


def animate(trays):
    last = 1 + FPS * SECONDS
    for t in trays:
        ob = t.obj
        ob.keyframe_insert("location", frame=1)
        ob.location.x = t.x0 + SPEED * SECONDS
        ob.keyframe_insert("location", frame=last)
        ob.location.x = t.x0
        for fc in ob.animation_data.action.fcurves:
            for k in fc.keyframe_points:
                k.interpolation = "LINEAR"


def build_conveyor():
    belt_mat, steel = mat_belt(), mat_steel()
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(BELT_LEN, BELT_W, 1))
    _obj_from_bmesh("belt", bm, belt_mat)

    for side in (-1, 1):
        bm = bmesh.new()
        v = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        bmesh.ops.scale(bm, verts=v, vec=(BELT_LEN, 0.05, 0.11))
        bmesh.ops.translate(bm, verts=v, vec=(0, side * (BELT_W / 2 + 0.025), -0.035))
        rail = _obj_from_bmesh(f"frame_{side}", bm, steel)
        bev = rail.modifiers.new("bevel", "BEVEL")
        bev.width = 0.003
        bev.segments = 2
        # low guide rail on posts, as on a real case conveyor
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.008,
                              radius2=0.008, depth=BELT_LEN)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                         matrix=Matrix.Rotation(math.pi / 2, 3, "Y"))
        bmesh.ops.translate(bm, verts=bm.verts,
                            vec=(0, side * (BELT_W / 2 - 0.004), 0.062))
        _obj_from_bmesh(f"guide_{side}", bm, steel)
        for px in [x * 0.6 - BELT_LEN / 2 for x in range(int(BELT_LEN / 0.6) + 1)]:
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.005,
                                  radius2=0.005, depth=0.05)
            bmesh.ops.translate(bm, verts=bm.verts,
                                vec=(px, side * (BELT_W / 2 - 0.004), 0.037))
            _obj_from_bmesh(f"post_{side}_{px:.1f}", bm, steel)

    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=6)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, -0.85))
    _obj_from_bmesh("floor", bm, mat_floor())

    # yellow safety-painted side panels below the belt line
    for side in (-1, 1):
        bm = bmesh.new()
        v = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        bmesh.ops.scale(bm, verts=v, vec=(BELT_LEN, 0.01, 0.7))
        bmesh.ops.translate(bm, verts=v, vec=(0, side * (BELT_W / 2 + 0.06), -0.45))
        _obj_from_bmesh(f"panel_{side}", bm, mat_plain("panel", (0.55, 0.38, 0.02), 0.55))


def build_lights_and_camera():
    sc = bpy.context.scene
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.5, 0.52, 0.55, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.08
    sc.world = world

    for name, loc, size, power in [("key", (0.5, -0.7, 2.2), 1.2, 110),
                                   ("fill", (-0.9, 0.8, 2.0), 1.2, 45),
                                   ("strip", (0.0, 0.0, 1.9), 0.25, 60)]:
        ld = bpy.data.lights.new(name, "AREA")
        ld.size = size
        ld.energy = power
        ld.color = (1.0, 0.97, 0.93)
        if name == "strip":
            ld.shape = "RECTANGLE"
            ld.size, ld.size_y = 4.0, 0.25
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        lo.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(lo)

    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = 30
    cam = bpy.data.objects.new("cam", cam_d)
    cam.location = (0.0, -0.42, 1.10)
    target = Vector((0.0, 0.0, 0.0))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def build(seed=SEED):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rng = random.Random(seed)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, FPS * SECONDS
    build_conveyor()
    trays = build_line(rng)
    animate(trays)
    cam = build_lights_and_camera()
    return trays, cam
