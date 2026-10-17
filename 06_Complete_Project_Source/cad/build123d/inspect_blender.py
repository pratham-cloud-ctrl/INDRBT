"""Inspect the saved Blender home scene against the current CAD mesh manifest.

Run: blender --background --python cad/build123d/inspect_blender.py
This reads the saved file without saving or rendering.
"""

import hashlib
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    mesh_path = ROOT / "cad/exports/meshes/assembly_meshes.json"
    data = json.loads(mesh_path.read_text())
    native = ROOT / "cad/renders/aster6_home.blend"
    bpy.ops.wm.open_mainfile(filepath=str(native))
    errors = []
    rows = []
    for c in data["components"]:
        obj = bpy.data.objects.get(c["name"])
        if obj is None:
            errors.append("Missing Blender object: " + c["name"])
            continue
        counts_match = len(obj.data.vertices) == len(c["vertices"]) and len(
            obj.data.polygons
        ) == len(c["triangles"])
        if not counts_match:
            errors.append("Mesh count mismatch: " + c["name"])
            continue
        ve = max(
            abs(obj.data.vertices[i].co[j] - v[j] * 0.001)
            for i, v in enumerate(c["vertices"])
            for j in range(3)
        )
        T = data["pose_transforms"]["home"][c["group"]]
        te = max(
            abs(obj.matrix_world[i][j] - T[i][j] * (0.001 if j == 3 and i < 3 else 1))
            for i in range(4)
            for j in range(4)
        )
        if ve > 1e-6 or te > 1e-6:
            errors.append("Mesh or transform mismatch: " + c["name"])
        rows.append(
            {
                "name": c["name"],
                "vertices": len(c["vertices"]),
                "triangles": len(c["triangles"]),
                "maximum_local_vertex_error_m": ve,
                "maximum_home_matrix_error": te,
            }
        )
    renders = sorted((ROOT / "cad/renders").glob("*.png"))
    result = {
        "status": "PASS" if not errors else "FAIL",
        "application": "Blender",
        "version": bpy.app.version_string,
        "mesh_sha256": digest(mesh_path),
        "native_sha256": digest(native),
        "components_checked": len(rows),
        "float_comparison_tolerance": 1e-6,
        "components": rows,
        "render_sha256": {p.name: digest(p) for p in renders},
        "errors": errors,
        "scope": "Saved native object names/counts, local CAD mesh vertices and home transforms are compared directly. PNG hashes bind the outputs from the rendering workflow; readability is checked by review_cad.py.",
    }
    target = ROOT / "results/validation/cad_blender_inspection.json"
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps({"status": result["status"], "components_checked": len(rows), "errors": errors}),
        flush=True,
    )
    if errors:
        raise RuntimeError("Saved Blender scene differs from current CAD mesh")
    return result


if __name__ == "__main__":
    main()
