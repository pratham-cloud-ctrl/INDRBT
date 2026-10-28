"""Headless Blender renderer of the actual CAD tessellation (not illustration).

Run: blender --background --python cad/build123d/render_blender.py
"""

import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[2]
DATA = json.loads((ROOT / "cad/exports/meshes/assembly_meshes.json").read_text())
OUT = ROOT / "cad/renders"
OUT.mkdir(parents=True, exist_ok=True)


def material(name, hexcolor, metal=0.7):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    srgb = tuple(int(hexcolor[i : i + 2], 16) / 255 for i in (1, 3, 5))
    rgb = tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in srgb)
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = 0.31 if metal else 0.53
    return m


def point(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def scene(pose="home", gripper=False):
    print("Building actual CAD mesh scene:", pose, "gripper=", gripper, flush=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    mats = {
        c["color"]: material(
            c["color"], c["color"], 0.05 if c["color"] in ("#243949", "#EDA34E") else 0.65
        )
        for c in DATA["components"]
    }
    for c in DATA["components"]:
        if gripper and c["group"] != "j6":
            continue
        mesh = bpy.data.meshes.new(c["name"])
        mesh.from_pydata([[a * 0.001 for a in v] for v in c["vertices"]], [], c["triangles"])
        mesh.update()
        obj = bpy.data.objects.new(c["name"], mesh)
        bpy.context.collection.objects.link(obj)
        if not gripper:
            T = Matrix(DATA["pose_transforms"][pose][c["group"]])
            T.translation *= 0.001
            obj.matrix_world = T
        obj.data.materials.append(mats[c["color"]])
        # Flat tessellation respects deliberately sharp milled surfaces. Mesh
        # triangles approximate cylinders within documented 0.5-mm tolerance.
    floor_z = -0.029 if gripper else -0.001
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, floor_z))
    floor = bpy.context.object
    floor.data.materials.append(material("stage", "#D2DADE", 0))
    print("Mesh objects created", flush=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 32
    sc.cycles.use_denoising = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.film_transparent = False
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.07, 0.09, 0.12, 1)
    bg.inputs["Strength"].default_value = 0.35
    for name, pos, power, size in [
        ("key", (0.3, -0.6, 1.5), 80, 1.0),
        ("fill", (-0.9, 0.3, 0.8), 35, 0.9),
        ("rim", (0.8, 0.8, 1.3), 95, 0.7),
    ]:
        bpy.ops.object.light_add(type="AREA", location=pos)
        light = bpy.context.object
        light.name = name
        light.data.energy = power
        light.data.shape = "DISK"
        light.data.size = size
        point(light, (0.25, 0, 0.3))
    bpy.ops.object.camera_add(location=(1.15, -1.45, 1.05) if not gripper else (0.23, -0.22, 0.16))
    cam = bpy.context.object
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.04 if not gripper else 0.255
    point(cam, (0.23, 0, 0.30) if not gripper else (0.06, 0.004, 0))
    sc.camera = cam
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = -1.0
    return sc


def render(pose, file, width, height, gripper=False):
    sc = scene(pose, gripper)
    sc.render.resolution_x = width
    sc.render.resolution_y = height
    sc.render.resolution_percentage = 100
    if file.startswith("pose_"):
        pts = [
            o.matrix_world @ v.co
            for o in bpy.context.scene.objects
            if o.type == "MESH" and not o.name.startswith("Plane")
            for v in o.data.vertices
        ]
        lo = Vector([min(v[i] for v in pts) for i in range(3)])
        hi = Vector([max(v[i] for v in pts) for i in range(3)])
        target = (lo + hi) / 2
        sc.camera.location = target + Vector((1.15, -1.45, 1.05))
        point(sc.camera, target)
        R = sc.camera.rotation_euler.to_matrix().transposed()
        proj = [R @ (v - target) for v in pts]
        dx = max(v.x for v in proj) - min(v.x for v in proj)
        dy = max(v.y for v in proj) - min(v.y for v in proj)
        cx = (max(v.x for v in proj) + min(v.x for v in proj)) / 2
        cy = (max(v.y for v in proj) + min(v.y for v in proj)) / 2
        sc.camera.location += sc.camera.rotation_euler.to_matrix() @ Vector((cx, cy, 0))
        sc.camera.data.ortho_scale = max(dx, dy * width / height) * 1.18
    sc.render.filepath = str(OUT / file)
    bpy.ops.render.render(write_still=True)
    print("Saved CAD render:", file, flush=True)


if "--poses-only" not in sys.argv:
    render("home", "hero.png", 1600, 1050)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "indrbt_home.blend"))
    render("home", "gripper.png", 1200, 850, True)
for pose in DATA["pose_transforms"]:
    render(pose, f"pose_{pose}.png", 700, 650)
