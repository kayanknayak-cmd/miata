"""Build and render a marble-music scene from plan.json + style.json.

Run:  blender -b -P blender_scene.py -- plan.json style.json out.mp4 [--preview]
      --preview: quarter resolution, 30 fps, few samples (fast check)
      --still F: render only frame F to out (PNG)

Works on Blender 4.2 LTS and newer (EEVEE engine id changed between versions).
"""
import json
import math
import sys

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
plan = json.load(open(argv[0]))
style = json.load(open(argv[1]))
out = argv[2]
PREVIEW = "--preview" in argv
STILL = int(argv[argv.index("--still") + 1]) if "--still" in argv else None

FPS = 30 if PREVIEW else style.get("fps", 60)
G = plan["gravity"]
R = plan["ball_radius"]
TH = plan["pad_thickness"]
DEPTH = style.get("pad_depth", 0.42)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS
N = int(math.ceil(plan["duration"] * FPS))
sc.frame_start, sc.frame_end = 1, N
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
sc.render.resolution_percentage = 25 if PREVIEW else 100


def ftime(f):
    return (f - 1) / FPS


def tframe(t):
    return 1 + t * FPS


# ---------------------------------------------------------------- engine
engine = style.get("engine", "eevee")
if engine == "eevee":
    for eid in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = eid
            break
        except TypeError:
            pass
    try:
        sc.eevee.taa_render_samples = 16 if PREVIEW else 64
        sc.eevee.use_shadows = True
        sc.eevee.use_raytracing = True
    except AttributeError:
        pass
else:
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 12 if PREVIEW else style.get("samples", 96)
    sc.cycles.use_denoising = True
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("METAL", "OPTIX", "CUDA", "HIP"):
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
                if any(d.type == kind for d in prefs.devices):
                    for d in prefs.devices:
                        d.use = True
                    sc.cycles.device = "GPU"
                    break
            except TypeError:
                continue
    except KeyError:
        pass
sc.view_settings.view_transform = style.get("view_transform", "Standard")
sc.view_settings.look = style.get("look", "AgX - Medium High Contrast") if sc.view_settings.view_transform == "AgX" else "None"
sc.view_settings.exposure = style.get("exposure", -0.7)


# ---------------------------------------------------------------- helpers
def hex2rgb(h):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb)


def node_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links


def set_input(node, names, value):
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return


def sock(node, name, out=False):
    """Mix nodes carry several hidden sockets with the same name; pick the live one."""
    return next(x for x in (node.outputs if out else node.inputs) if x.name == name and x.enabled)


palette = [hex2rgb(c) for c in style["palette"]]


def pad_color(pitch):
    return palette[(pitch * 7) % 12 % len(palette)]  # circle of fifths spreads neighbours apart


# ---------------------------------------------------------------- world + backdrop
world = bpy.data.worlds.new("W")
sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (*hex2rgb(style["bg_top"]), 1)
bg.inputs[1].default_value = style.get("world_strength", 0.6)

ys = [p["pos"][1] for p in plan["pads"]]
top = plan["segments"][0]["p0"][1] + 6
bottom = min(ys) - 14
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, (top + bottom) / 2, -style.get("wall_dist", 0.9)))
wall = bpy.context.object
wall.location.z = -style.get("wall_dist", 2.2)
wall.scale = (60, top - bottom, 1)
wm, nodes, links = node_mat("Wall")
bsdf = nodes["Principled BSDF"]
tc = nodes.new("ShaderNodeTexCoord")
sep = nodes.new("ShaderNodeSeparateXYZ")
ramp = nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (*hex2rgb(style["bg_bottom"]), 1)
ramp.color_ramp.elements[1].color = (*hex2rgb(style["bg_top"]), 1)
links.new(tc.outputs["Generated"], sep.inputs[0])
links.new(sep.outputs["Y"], ramp.inputs[0])
links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
set_input(bsdf, ["Roughness"], 0.85)
wall.data.materials.append(wm)

# ---------------------------------------------------------------- lights
sun_d = bpy.data.lights.new("Sun", "SUN")
sun_d.energy = style.get("sun", 3.0)
sun_d.angle = math.radians(style.get("shadow_softness", 12))
sun = bpy.data.objects.new("Sun", sun_d)
sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(style.get("sun_tilt", -14)), math.radians(style.get("sun_pan", -10)), 0)

# ---------------------------------------------------------------- pad material (per-object colour drives glow)
pm, nodes, links = node_mat("Pad")
bsdf = nodes["Principled BSDF"]
oi = nodes.new("ShaderNodeObjectInfo")
# unplayed pads are pale "ghosts"; object alpha > 0 (hit) snaps them to full colour
lit = nodes.new("ShaderNodeMath")
lit.operation = "MULTIPLY"
lit.use_clamp = True
lit.inputs[1].default_value = 20.0
links.new(oi.outputs["Alpha"], lit.inputs[0])
ghost = nodes.new("ShaderNodeMix")
ghost.data_type = "RGBA"
sock(ghost, "A").default_value = (*hex2rgb(style.get("ghost", "#ffffff")), 1)
links.new(lit.outputs[0], sock(ghost, "Factor"))
links.new(oi.outputs["Color"], sock(ghost, "B"))
gfac = style.get("ghost_mix", 0.6)  # how pale unplayed pads are
blend = nodes.new("ShaderNodeMix")
blend.data_type = "RGBA"
sock(blend, "Factor").default_value = 1 - gfac
links.new(sock(ghost, "Result", True), sock(blend, "A"))
links.new(oi.outputs["Color"], sock(blend, "B"))
# final: lit pads full colour, ghost pads = mix(ghost, colour, 1-gfac)
final = nodes.new("ShaderNodeMix")
final.data_type = "RGBA"
links.new(lit.outputs[0], sock(final, "Factor"))
links.new(sock(blend, "Result", True), sock(final, "A"))
links.new(oi.outputs["Color"], sock(final, "B"))
links.new(sock(final, "Result", True), bsdf.inputs["Base Color"])
set_input(bsdf, ["Roughness"], style.get("pad_roughness", 0.25))
set_input(bsdf, ["Coat Weight", "Clearcoat"], style.get("pad_coat", 0.6))
set_input(bsdf, ["Metallic"], style.get("pad_metallic", 0.0))
emit_col = "Emission Color" if "Emission Color" in bsdf.inputs else "Emission"
links.new(oi.outputs["Color"], bsdf.inputs[emit_col])
mul = nodes.new("ShaderNodeMath")
mul.operation = "MULTIPLY"
mul.inputs[1].default_value = style.get("glow", 6.0)
links.new(oi.outputs["Alpha"], mul.inputs[0])
links.new(mul.outputs[0], bsdf.inputs["Emission Strength"])

# ring burst material: emission, fades with object alpha
rm, nodes, links = node_mat("Ring")
for n in list(nodes):
    if n.type != "OUTPUT_MATERIAL":
        nodes.remove(n)
oi = nodes.new("ShaderNodeObjectInfo")
em = nodes.new("ShaderNodeEmission")
em.inputs[1].default_value = style.get("ring_glow", 4.0)
tr = nodes.new("ShaderNodeBsdfTransparent")
mix = nodes.new("ShaderNodeMixShader")
links.new(oi.outputs["Color"], em.inputs[0])
links.new(oi.outputs["Alpha"], mix.inputs[0])
links.new(tr.outputs[0], mix.inputs[1])
links.new(em.outputs[0], mix.inputs[2])
links.new(mix.outputs[0], nodes["Material Output"].inputs[0])
for attr, val in (("blend_method", "BLEND"), ("surface_render_method", "BLENDED")):
    try:
        setattr(rm, attr, val)
    except (AttributeError, TypeError):
        pass


# ---------------------------------------------------------------- pad meshes (rounded bars, shared per width)
_mesh_cache = {}


def pad_mesh(width):
    key = round(width, 2)
    if key not in _mesh_cache:
        bpy.ops.mesh.primitive_cube_add(size=1)
        o = bpy.context.object
        o.scale = (key, TH, DEPTH)
        bpy.ops.object.transform_apply(scale=True)
        bev = o.modifiers.new("b", "BEVEL")
        bev.width = TH * 0.45
        bev.segments = 4
        bpy.ops.object.modifier_apply(modifier="b")
        bpy.ops.object.shade_smooth()
        o.data.materials.append(pm)
        _mesh_cache[key] = o.data
        bpy.data.objects.remove(o)
    return _mesh_cache[key]


bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.035, major_segments=48, minor_segments=8)
ring_proto = bpy.context.object
ring_mesh = ring_proto.data
ring_mesh.materials.append(rm)
bpy.data.objects.remove(ring_proto)


def key_color(o, f, rgb, a):
    o.color = (*rgb, a)
    o.keyframe_insert("color", frame=f)


base_glow = max(0.06, style.get("glow_after", 0.12))
for i, p in enumerate(plan["pads"]):
    o = bpy.data.objects.new(f"pad{i:03d}", pad_mesh(p["width"]))
    sc.collection.objects.link(o)
    tx, ty = p["tangent"]
    o.rotation_euler = (0, 0, math.atan2(ty, tx))
    nx, ny = p["normal"]
    x, y = p["pos"]
    rgb = pad_color(max(p["pitches"]))
    hf = tframe(p["time"])
    # glow: off -> flash on hit -> settles to a dim "lit" state (shows the path played so far)
    key_color(o, 1, rgb, 0.0)
    key_color(o, hf - 1, rgb, 0.0)
    key_color(o, hf, rgb, 1.0)
    key_color(o, hf + 0.45 * FPS, rgb, base_glow)
    # recoil along -normal, damped spring back
    for dt, d in ((-1 / FPS, 0), (0, 0), (0.05, -0.07), (0.12, 0.03), (0.2, -0.012), (0.3, 0)):
        o.location = (x + nx * d, y + ny * d, 0)
        o.keyframe_insert("location", frame=hf + dt * FPS)
    # ring burst at the contact point, facing along the pad normal
    if style.get("rings", True):
        r = bpy.data.objects.new(f"ring{i:03d}", ring_mesh)
        sc.collection.objects.link(r)
        hx, hy = p["hit"]
        r.location = (hx - nx * R, hy - ny * R, 0)
        r.visible_shadow = False
        for f, s, a in ((1, 0.001, 0), (hf - 1, 0.001, 0), (hf, 0.15, 0.9), (hf + 0.3 * FPS, 0.38, 0.0)):
            r.scale = (s, s, s)
            r.keyframe_insert("scale", frame=f)
            key_color(r, f, rgb, a)

# ---------------------------------------------------------------- ball
bpy.ops.mesh.primitive_uv_sphere_add(radius=R, segments=48, ring_count=24)
ball = bpy.context.object
bpy.ops.object.shade_smooth()
bm, nodes, links = node_mat("Ball")
b = nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (*hex2rgb(style["ball"]), 1)
set_input(b, ["Metallic"], style.get("ball_metallic", 0.0))
set_input(b, ["Roughness"], style.get("ball_roughness", 0.12))
set_input(b, ["Coat Weight", "Clearcoat"], 1.0)
ball.data.materials.append(bm)


def ball_at(t):
    for s in plan["segments"]:
        if t <= s["t1"] or s is plan["segments"][-1]:
            d = max(0.0, t - s["t0"])
            return (s["p0"][0] + s["v0"][0] * d, s["p0"][1] + s["v0"][1] * d - 0.5 * G * d * d)


def set_fcurve(obj, path, index, pts):
    if obj.animation_data is None:
        obj.animation_data_create()
    if obj.animation_data.action is None:
        obj.animation_data.action = bpy.data.actions.new(obj.name + "Act")
    act = obj.animation_data.action
    fc = None
    try:
        fc = act.fcurves.new(path, index=index)
    except Exception:  # Blender 5 layered actions
        fc = act.fcurve_ensure_for_datablock(obj, path, index=index)
    fc.keyframe_points.add(len(pts))
    flat = [c for pt in pts for c in pt]
    fc.keyframe_points.foreach_set("co", flat)
    for kp in fc.keyframe_points:
        kp.interpolation = "LINEAR"
    fc.update()


# sample on a 2x sub-frame grid so motion blur and bounces stay exact
fr = [1 + i * 0.5 for i in range(2 * N + 1)]
pos = [ball_at(ftime(f)) for f in fr]
# make sure the exact contact instants are keyed
extra = [(tframe(p["time"]), tuple(p["hit"])) for p in plan["pads"]]
allp = sorted(list(zip(fr, pos)) + extra)
set_fcurve(ball, "location", 0, [(f, p[0]) for f, p in allp])
set_fcurve(ball, "location", 1, [(f, p[1]) for f, p in allp])
# rolling spin: angle follows horizontal travel
ang, last, spins = 0.0, allp[0][1][0], []
for f, p in allp:
    ang -= (p[0] - last) / R
    last = p[0]
    spins.append((f, ang))
set_fcurve(ball, "rotation_euler", 2, spins)

# ---------------------------------------------------------------- camera (smoothed follow)
cam_d = bpy.data.cameras.new("Cam")
cam_d.lens = style.get("lens", 54)
cam_d.sensor_fit = "VERTICAL"
cam_d.sensor_height = 36
cam = bpy.data.objects.new("Cam", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
off = Vector(style.get("cam_offset", [1.6, 2.2, 8.6]))
# explicit look-at basis (world +Y stays screen-up): camera looks along -Z, up is +Y
fwd = (-off).normalized()
right = fwd.cross(Vector((0, 1, 0))).normalized()
up = right.cross(fwd)
cam.rotation_euler = Matrix((right, up, -fwd)).transposed().to_euler()
win = int(0.45 * FPS)
ys_f = [ball_at(ftime(f))[1] for f in range(1, N + 1)]
lead = style.get("cam_lead", 0.9)  # keep the ball above centre so upcoming pads are visible
cam_pts_y = []
for i in range(N):
    a, bnd = max(0, i - win), min(N, i + win + 1)
    cam_pts_y.append((i + 1, sum(ys_f[a:bnd]) / (bnd - a) - lead + off.y))
set_fcurve(cam, "location", 1, cam_pts_y)
cam.location.x, cam.location.z = off.x, off.z

# ---------------------------------------------------------------- hook text (parented to camera)
if style.get("hook"):
    tcu = bpy.data.curves.new("hook", "FONT")
    tcu.body = style["hook"]
    tcu.align_x = "CENTER"
    for fp in style.get("fonts", []) + [
        "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/usr/share/fonts/opentype/inter/Inter-Black.otf",
    ]:
        try:
            tcu.font = bpy.data.fonts.load(fp)
            break
        except (RuntimeError, OSError):
            continue
    tcu.size = 0.085
    tcu.extrude = 0.0
    txt = bpy.data.objects.new("hook", tcu)
    sc.collection.objects.link(txt)
    txt.parent = cam
    txt.location = (0, 0.56, -2)  # near the top of frame, in camera space
    txt.visible_shadow = False
    tm, nodes, links = node_mat("Text")
    for n in list(nodes):
        if n.type != "OUTPUT_MATERIAL":
            nodes.remove(n)
    e = nodes.new("ShaderNodeEmission")
    e.inputs[0].default_value = (*hex2rgb(style.get("text", "#ffffff")), 1)
    e.inputs[1].default_value = 1.0
    links.new(e.outputs[0], nodes["Material Output"].inputs[0])
    tcu.materials.append(tm)
    # dark drop shadow copy for legibility on any background
    sh = bpy.data.objects.new("hook_shadow", tcu.copy())
    sc.collection.objects.link(sh)
    sh.parent = cam
    sh.location = (0.005, 0.555, -2.002)
    sh.visible_shadow = False
    sm, nodes, links = node_mat("TextShadow")
    for n in list(nodes):
        if n.type != "OUTPUT_MATERIAL":
            nodes.remove(n)
    e = nodes.new("ShaderNodeEmission")
    e.inputs[0].default_value = (0, 0, 0, 1)
    e.inputs[1].default_value = 0.0
    links.new(e.outputs[0], nodes["Material Output"].inputs[0])
    sh.data.materials.clear()
    sh.data.materials.append(sm)

# ---------------------------------------------------------------- compositor glow
if style.get("bloom", 0) > 0:
    sc.use_nodes = True
    nt = sc.node_tree
    rl, comp = nt.nodes["Render Layers"], nt.nodes["Composite"]
    gl = nt.nodes.new("CompositorNodeGlare")
    gl.glare_type = "FOG_GLOW"
    try:
        gl.mix = -1 + style["bloom"]
        gl.threshold = style.get("bloom_threshold", 1.0)
    except AttributeError:
        pass
    nt.links.new(rl.outputs["Image"], gl.inputs[0])
    nt.links.new(gl.outputs[0], comp.inputs["Image"])

sc.render.use_motion_blur = not PREVIEW and style.get("motion_blur", True)

# ---------------------------------------------------------------- output
if STILL is not None:
    sc.frame_set(STILL)
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
else:
    sc.render.image_settings.file_format = "FFMPEG"
    sc.render.ffmpeg.format = "MPEG4"
    sc.render.ffmpeg.codec = "H264"
    sc.render.ffmpeg.constant_rate_factor = "HIGH"
    sc.render.ffmpeg.ffmpeg_preset = "GOOD"
    sc.render.filepath = out
    bpy.ops.render.render(animation=True)
