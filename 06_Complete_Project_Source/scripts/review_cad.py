"""Audit current CAD exports and native evidence; never refresh stale proof blindly.

Run after generate_cad.py, FreeCAD inspection, Blender rendering/composition/
inspection and check_motion.py. Requires the [cad,dev] project extras.
"""

from datetime import datetime, timezone
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
from build123d import Shape, Vector, import_step, Pos
from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cad/build123d"))
from parameters import parameters  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def intersection_volume(a, b):
    common = a & b
    return float(common.volume) if common else 0.0


def audit():
    issues = []
    cfg, p = parameters()
    cad = read("results/validation/cad_validation.json")
    mesh = read("cad/exports/meshes/assembly_meshes.json")
    fc = read("results/validation/cad_freecad_inspection.json")
    blender = read("results/validation/cad_blender_inspection.json")
    clearance = read("results/validation/cad_assembly_clearance.json")
    motion = read("results/validation/cad_motion_clearance.json")

    def require(condition, message):
        if not condition:
            issues.append(message)

    sources = [
        "config/robot.yaml",
        "cad/build123d/geometry.py",
        "cad/build123d/assembly.py",
        "cad/build123d/parameters.py",
        "cad/build123d/export_all.py",
        "cad/build123d/drawings.py",
        "cad/build123d/render_blender.py",
        "cad/build123d/inspect_blender.py",
        "cad/freecad/inspect_step.py",
        "cad/build123d/check_assembly.py",
        "cad/build123d/check_motion.py",
        "scripts/review_cad.py",
        "scripts/refresh_cad.py",
        "tests/test_cad.py",
    ]
    for evidence in (cad, clearance, motion):
        for key, expected in evidence["source_sha256"].items():
            source = "config/robot.yaml" if key == "robot.yaml" else "cad/build123d/geometry.py"
            require(
                digest(ROOT / source) == expected,
                "Stale geometry/configuration evidence: " + source,
            )
    require(clearance["status"] == motion["status"] == "PASS", "Clearance did not pass")
    require(
        digest(ROOT / "results/trajectories/pick_place_samples.json")
        == motion["trajectory_sha256"],
        "Stale trajectory clearance",
    )
    mesh_hash = digest(ROOT / "cad/exports/meshes/assembly_meshes.json")
    require(
        fc["mesh_sha256"] == blender["mesh_sha256"] == mesh_hash,
        "Native evidence uses stale mesh manifest",
    )
    require(
        fc["native_sha256"] == digest(ROOT / "cad/freecad/aster6_home.FCStd"),
        "FreeCAD native evidence is stale",
    )
    require(
        blender["status"] == "PASS" and not blender["errors"], "Blender native inspection failed"
    )
    require(
        blender["native_sha256"] == digest(ROOT / "cad/renders/aster6_home.blend"),
        "Blender native evidence is stale",
    )
    for name, expected in blender["render_sha256"].items():
        require(
            digest(ROOT / "cad/renders" / name) == expected,
            "Render differs from inspected output: " + name,
        )
    require(
        len(blender["render_sha256"]) == 9,
        "Expected hero, gripper, six poses and combined pose PNGs",
    )

    shapes = {}
    rows = []
    for c in cad["components"]:
        name = c["name"]
        s = import_step(ROOT / f"cad/exports/STEP/{name}.step")
        shapes[name] = s
        box = s.bounding_box()
        volume_error = abs(s.volume - c["volume_mm3"]) / c["volume_mm3"]
        bbox_error = max(
            np.max(np.abs(np.array(list(box.min)) - c["bbox"]["min_mm"])),
            np.max(np.abs(np.array(list(box.max)) - c["bbox"]["max_mm"])),
        )
        raw = (ROOT / f"cad/exports/STL/{name}.stl").read_bytes()
        n = struct.unpack_from("<I", raw, 80)[0]
        dtype = np.dtype(
            [("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")]
        )
        verts = np.frombuffer(raw, dtype=dtype, offset=84, count=n)["vertices"].reshape(-1, 3)
        stl_error = max(
            np.max(np.abs(verts.min(0) - c["bbox"]["min_mm"])),
            np.max(np.abs(verts.max(0) - c["bbox"]["max_mm"])),
        )
        require(
            s.is_valid and len(s.solids()) == 1 and volume_error < 1e-6 and bbox_error < 1e-5,
            "Invalid/different component STEP: " + name,
        )
        require(
            len(raw) == 84 + 50 * n and stl_error <= 0.5, "Invalid/different component STL: " + name
        )
        rows.append(
            {
                "name": name,
                "valid": bool(s.is_valid),
                "solids": len(s.solids()),
                "volume_relative_error": float(volume_error),
                "bbox_error_mm": float(bbox_error),
                "stl_bbox_error_mm": float(stl_error),
                "triangles": n,
            }
        )
    expected_names = set(shapes) | {"assembly_" + name for name in cad["poses"]}
    for kind, ext in (("STEP", "step"), ("STL", "stl")):
        require(
            {x.stem for x in (ROOT / "cad/exports" / kind).glob("*." + ext)} == expected_names,
            "Missing or orphan " + kind + " exports",
        )
    require({c["name"] for c in mesh["components"]} == set(shapes), "Mesh component names differ")
    dimensions = []
    for part, axis, key in [
        ("base_mounting_plate", 0, "base_diameter"),
        ("tool_flange_6xM5_PCD46", 1, "tool_flange_diameter"),
        ("upper_arm_hollow_link", 1, "upper_arm_width"),
        ("upper_arm_hollow_link", 2, "upper_arm_depth"),
        ("forearm_hollow_link", 1, "forearm_width"),
        ("forearm_hollow_link", 2, "forearm_depth"),
        ("gripper_finger_+1", 0, "finger_length"),
        ("gripper_finger_+1", 1, "finger_thickness"),
        ("gripper_finger_+1", 2, "finger_width"),
    ]:
        actual = list(shapes[part].bounding_box().size)[axis]
        require(abs(actual - p[key]) < 1e-6, "Configuration dimension mismatch: " + key)
        dimensions.append({"dimension": key, "configured_mm": p[key], "exported_mm": actual})
    poses = []
    for name, record in cad["poses"].items():
        path = ROOT / f"cad/exports/STEP/assembly_{name}.step"
        s = import_step(path)
        bbox_error = float(
            np.max(np.abs(np.array(list(s.bounding_box().size)) - record["bbox"]["size_mm"]))
        )
        require(
            s.is_valid and len(s.solids()) == len(shapes) and bbox_error < 1e-5,
            "Invalid/different assembly: " + name,
        )
        require(
            record["q_deg"] == cfg["poses_deg"][name],
            "Assembly pose differs from configuration: " + name,
        )
        require(fc["step_sha256"][name] == digest(path), "FreeCAD STEP inspection stale: " + name)
        poses.append(
            {
                "pose": name,
                "valid": bool(s.is_valid),
                "solids": len(s.solids()),
                "bbox_error_mm": bbox_error,
            }
        )

    native_rows = []
    with zipfile.ZipFile(ROOT / "cad/freecad/aster6_home.FCStd") as archive:
        require(archive.testzip() is None, "FreeCAD archive CRC error")
        xml = ET.fromstring(archive.read("GuiDocument.xml"))
        visible = [
            x
            for x in xml.findall(".//ViewProvider")
            if x.find("./Properties/Property[@name='Visibility']/Bool") is not None
            and x.find("./Properties/Property[@name='Visibility']/Bool").get("value") == "true"
        ]
        require(len(visible) == len(shapes), "Native FreeCAD assembly opens with hidden solids")
        for mapping in fc["native_components"]:
            occ = TopoDS_Shape()
            BRepTools.Read_s(
                occ, BytesIO(archive.read(mapping["object"] + ".Shape.brp")), BRep_Builder()
            )
            s = Shape.cast(occ)
            c = next(x for x in cad["components"] if x["name"] == mapping["component"])
            T = np.array(mesh["pose_transforms"]["home"][c["group"]])
            target = (T @ np.append(c["center_of_geometry_mm"], 1))[:3]
            center_error = float(np.linalg.norm(np.array(list(s.center())) - target))
            volume_error = abs(s.volume - c["volume_mm3"]) / c["volume_mm3"]
            require(
                s.is_valid and len(s.solids()) == 1 and center_error < 1e-4 and volume_error < 1e-6,
                "Native solid differs: " + c["name"],
            )
            native_rows.append(
                {
                    "component": c["name"],
                    "object": mapping["object"],
                    "center_error_mm": center_error,
                    "volume_relative_error": volume_error,
                }
            )

    # Test exported material, not only generator source: fastening stack, counterbore,
    # real locating pilot, connected nut bosses, finger seats and nonintersecting hatch.
    interface_checks = []

    def material_check(name, point, expected, explanation):
        actual = bool(shapes[name].is_inside(Vector(*point)))
        require(actual == expected, explanation)
        interface_checks.append({"check": explanation, "matches": actual == expected})

    from math import cos, sin, pi

    for i in range(6):
        a = i * pi / 3
        for name, x in (
            ("tool_flange_6xM5_PCD46", 4),
            ("interchangeable_gripper_adapter", 12),
            ("gripper_pocketed_body", 18),
        ):
            material_check(
                name, (x, 23 * cos(a), 23 * sin(a)), False, f"{name}: bolt {i + 1} clearance"
            )
        material_check(
            "interchangeable_gripper_adapter",
            (12, 28 * cos(a), 28 * sin(a)),
            True,
            f"Adapter bolt {i + 1} outer ligament",
        )
    material_check("base_mounting_plate", (97, 0, 12.9), True, "Counterbore bottom below Z13")
    material_check("base_mounting_plate", (97, 0, 13.1), False, "Counterbore depth reaches 7 mm")
    material_check("tool_flange_6xM5_PCD46", (10, 14, 0), True, "Real OD30 pilot spigot")
    material_check("gripper_pocketed_body", (18, 0, 0), False, "Rear cable entrance")
    material_check("upper_arm_hollow_link", (100, 38, 34), True, "Upper nominal wall material")
    material_check("upper_arm_hollow_link", (100, 35.9, 34), False, "Upper nominal inner wall")
    material_check("forearm_hollow_link", (120, 30.5, 30), True, "Forearm nominal wall material")
    material_check("forearm_hollow_link", (120, 28.4, 30), False, "Forearm nominal inner wall")
    for side in (-1, 1):
        y = side * (p["opening"] / 2 + p["finger_thickness"] / 2 + 1.5)
        name = f"gripper_jaw_carriage_{side:+}"
        for point, solid, label in [
            ((28, y, 5), True, "nut boss"),
            ((36, y, 0), True, "connected bridge"),
            ((28, y, 0), False, "nut screw clearance"),
            ((59, y, -12), True, "finger support tab"),
        ]:
            material_check(name, point, solid, name + ": " + label)
        finger = shapes[f"gripper_finger_{side:+}"]
        require(
            shapes[name].distance_to(finger) < 1e-6
            and intersection_volume(shapes[name], finger) < 1e-6,
            "Finger seat gap or overlap",
        )
    cover = shapes["gripper_top_service_cover"]
    require(
        intersection_volume(cover, shapes["gripper_pocketed_body"]) < 1e-6
        and intersection_volume(cover, shapes["interchangeable_gripper_adapter"]) < 1e-6,
        "Service hatch interferes",
    )
    grip = []
    for gap in (0, p["opening"] / 4, p["opening"] / 2, 3 * p["opening"] / 4, p["opening"]):
        moving = {}
        for name, shape in shapes.items():
            if name.startswith(
                ("gripper_jaw_carriage_", "gripper_finger_", "gripper_contact_pad_")
            ):
                side = 1 if name.endswith("+1") else -1
                moving[name] = shape.moved(Pos(0, side * (gap - p["opening"]) / 2, 0))
        measured = (
            moving["gripper_contact_pad_+1"].bounding_box().min.Y
            - moving["gripper_contact_pad_-1"].bounding_box().max.Y
        )
        overlaps = [
            intersection_volume(s, shapes["gripper_pocketed_body"]) for s in moving.values()
        ]
        overlaps.append(
            intersection_volume(
                moving["gripper_jaw_carriage_+1"], moving["gripper_jaw_carriage_-1"]
            )
        )
        require(
            abs(measured - gap) < 1e-5 and max(overlaps) < 1e-3,
            "Gripper gap/interference at " + str(gap),
        )
        grip.append(
            {
                "opening_mm": gap,
                "actual_pad_gap_mm": float(measured),
                "exact_pair_checks": len(overlaps),
                "maximum_overlap_mm3": float(max(overlaps)),
            }
        )

    images = {}
    for path in sorted((ROOT / "cad/renders").glob("*.png")):
        with Image.open(path) as image:
            images[path.name] = list(image.size)
            image.verify()
    drawing_annotations = []
    for path in (ROOT / "docs/drawings").glob("*.svg"):
        ET.parse(path)
        labels = path.read_text(encoding="utf-8")
        expected = {
            "01_base_tool_interfaces.svg": [
                "Ø220",
                "Ø17 counterbore, 7 deep",
                "Adapter Ø60 × 8 / bore Ø30.2",
            ],
            "02_link_sections.svg": [
                f"{p['upper_arm_length']:g} joint-center spacing",
                f"FOREARM: {p['forearm_length']:g} center spacing",
            ],
            "03_gripper_layout.svg": [
                f"{p['opening']:g} max clear opening",
                f"{p['finger_length']:g} finger",
                "Ø12 nut boss / Ø8.4 bore",
            ],
        }[path.name]
        for label in expected:
            require(label in labels, "Drawing annotation missing: " + label)
            drawing_annotations.append(
                {"sheet": path.name, "annotation": label, "matches": label in labels}
            )
    pdf = (ROOT / "docs/drawings/engineering_interfaces.pdf").read_bytes()
    require(
        pdf.startswith(b"%PDF-")
        and pdf.rstrip().endswith(b"%%EOF")
        and len(re.findall(rb"/Type\s*/Page\b", pdf)) == 3,
        "Drawing PDF is invalid",
    )
    artifacts = []
    for folder, pattern in [
        ("cad/exports/STEP", "*.step"),
        ("cad/exports/STL", "*.stl"),
        ("cad/renders", "*.png"),
        ("docs/drawings", "*"),
    ]:
        artifacts.extend(x for x in (ROOT / folder).glob(pattern) if x.is_file())
    artifacts += [
        ROOT / x
        for x in [
            "cad/freecad/aster6_home.FCStd",
            "cad/renders/aster6_home.blend",
            "cad/exports/meshes/assembly_meshes.json",
            "results/validation/cad_validation.json",
            "results/validation/cad_assembly_clearance.json",
            "results/validation/cad_motion_clearance.json",
            "results/validation/cad_freecad_inspection.json",
            "results/validation/cad_blender_inspection.json",
        ]
    ]
    return {
        "schema_version": 2,
        "status": "PASS" if not issues else "FAIL",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "issues": issues,
        "source_sha256": {f: digest(ROOT / f) for f in sources},
        "checked_artifacts": [
            {
                "file": str(x.relative_to(ROOT)).replace("\\", "/"),
                "sha256": digest(x),
                "bytes": x.stat().st_size,
            }
            for x in sorted(artifacts)
        ],
        "component_count": len(shapes),
        "configuration_dimensions": dimensions,
        "drawing_annotations": drawing_annotations,
        "component_correspondence": rows,
        "assembly_correspondence": poses,
        "native_components": native_rows,
        "saved_visible_components": len(visible),
        "mechanical_interface_checks": interface_checks,
        "gripper_range": grip,
        "render_dimensions": images,
        "clearance_summary": {
            "named_poses_exact_checks": clearance["exact_brep_pair_checks"],
            "motion_samples": motion["samples_checked"],
            "motion_exact_checks": motion["exact_brep_pair_checks"],
            "maximum_motion_overlap_mm3": motion["max_all_pair_overlap_mm3"],
        },
        "geometric_envelope_mass_kg": cad["geometric_mass_total_kg"],
        "scope": "Current exported STEP/STL correspondence, all native FreeCAD solids and saved visibility, hash-bound native Blender/FreeCAD inspection, actual exported fastening/nut/finger/hatch interfaces, five gripper gaps and 35 exact selected jaw/body intersections, retained all-pair named/task clearance and drawing/render readability. No source geometry is regenerated by this audit.",
        "limitations": "Digital concept: no continuous collision guarantee, all-configuration validation, thread/contact/preload simulation, production tolerances, cable bend qualification or physical performance certification.",
    }


def main():
    target = ROOT / "results/validation/cad_release_consistency.json"
    try:
        result = audit()
    except Exception as exc:
        result = {
            "status": "FAIL",
            "issues": [f"{type(exc).__name__}: {exc}"],
            "recorded_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "Audit stopped; no PASS proof was generated.",
        }
    for name in ("cad_release_consistency.json", "final_cad_review.json"):
        (target.parent / name).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "issues": result["issues"],
                "components": result.get("component_count"),
            }
        ),
        flush=True,
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
