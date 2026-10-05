"""Export actual OpenCascade geometry and its measured properties."""

import argparse
import json
import sys
import numpy as np
from build123d import export_step, export_stl, import_step
from parameters import ROOT, parameters
from geometry import build_components
from assembly import assemble, location, group_transforms
from check_assembly import create_report


def bounds(shape):
    b = shape.bounding_box()
    return {"min_mm": list(b.min), "max_mm": list(b.max), "size_mm": list(b.size)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-assembly-stl", action="store_true")
    args = parser.parse_args()
    cfg, p = parameters()
    comps = build_components(p)
    for folder in (
        "cad/exports/STEP",
        "cad/exports/STL",
        "cad/exports/meshes",
        "cad/renders",
        "results/validation",
    ):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    rows = []
    mesh_rows = []
    density = cfg["materials"]
    for c in comps:
        if not c.shape.is_valid or c.shape.volume <= 0:
            raise ValueError(f"Invalid or zero-volume CAD component: {c.name}")
        export_step(c.shape, ROOT / f"cad/exports/STEP/{c.name}.step")
        export_stl(
            c.shape, ROOT / f"cad/exports/STL/{c.name}.stl", tolerance=0.35, angular_tolerance=0.2
        )
        vol = c.shape.volume
        row = {
            "name": c.name,
            "group": c.group,
            "material": c.material,
            "role": c.role,
            "volume_mm3": vol,
            "density_kg_m3": density[c.material]["density"],
            "geometric_mass_kg": vol * 1e-9 * density[c.material]["density"],
            "center_of_geometry_mm": list(c.shape.center()),
            "solids": len(c.shape.solids()),
            "faces": len(c.shape.faces()),
            "valid": bool(c.shape.is_valid),
            "bbox": bounds(c.shape),
        }
        rows.append(row)
        vertices, triangles = c.shape.tessellate(0.5, 0.25)
        mesh_rows.append(
            {
                "name": c.name,
                "group": c.group,
                "color": c.color,
                "vertices": [[round(v.X, 5), round(v.Y, 5), round(v.Z, 5)] for v in vertices],
                "triangles": [list(t) for t in triangles],
            }
        )
    pose_rows = {}
    transform_rows = {}
    sys.path.insert(0, str(ROOT / "src"))
    from robotarm.kinematics import RobotArm

    arm = RobotArm()
    for name, q in cfg["poses_deg"].items():
        a, Ts = assemble(comps, q, p)
        filepath = ROOT / f"cad/exports/STEP/assembly_{name}.step"
        export_step(a, filepath)
        if not args.skip_assembly_stl:
            export_stl(
                a,
                ROOT / f"cad/exports/STL/assembly_{name}.stl",
                tolerance=0.5,
                angular_tolerance=0.25,
            )
        imported = import_step(filepath)
        # Every group transform is compared against the independent numerical
        # robot model. Rotation and translation must agree, not just reach.
        fk_frames = arm.frames(np.deg2rad(q))["link_transforms"]
        err = []
        for i in range(6):
            cadT = Ts[f"j{i + 1}"].copy()
            cadT[:3, 3] /= 1000
            err.append(float(np.max(np.abs(cadT - fk_frames[i]))))
        if max(err) > 1e-10:
            raise ValueError(f"CAD/FK frame mismatch: {name}: {err}")
        pose_rows[name] = {
            "q_deg": q,
            "bbox": bounds(a),
            "component_count": len(comps),
            "step_reimport_valid": bool(imported.is_valid),
            "step_reimport_solids": len(imported.solids()),
            "step_volume_relative_error": abs(imported.volume - a.volume) / a.volume,
            "max_cad_fk_transform_error": max(err),
        }
        transform_rows[name] = {k: v.tolist() for k, v in Ts.items()}
        print(
            f"CAD pose {name}: {len(imported.solids())} solids, reimport valid={imported.is_valid}",
            flush=True,
        )
    # Representative exact BRep interference checks between nonadjacent primary
    # structures. Bearings, shaft seats and motor envelopes are deliberately
    # excluded: envelope overlap or zero-clearance fits are not collision claims.
    byname = {c.name: c for c in comps}
    check_pairs = [
        ("base_mounting_plate", "upper_arm_hollow_link"),
        ("base_mounting_plate", "forearm_hollow_link"),
        ("fixed_base_riser", "forearm_hollow_link"),
        ("upper_arm_hollow_link", "forearm_hollow_link"),
        ("shoulder_fork_+1", "forearm_hollow_link"),
        ("upper_arm_hollow_link", "gripper_pocketed_body"),
    ]
    checks = []
    for pose, q in cfg["poses_deg"].items():
        Ts = group_transforms(q, p)
        for an, bn in check_pairs:
            ca, cb = byname[an], byname[bn]
            A = ca.shape.moved(location(Ts[ca.group]))
            B = cb.shape.moved(location(Ts[cb.group]))
            common = A & B
            overlap = common.volume if common else 0
            checks.append(
                {
                    "pose": pose,
                    "parts": [an, bn],
                    "overlap_mm3": float(overlap),
                    "result": "PASS" if overlap < 1e-3 else "INTERFERENCE",
                }
            )
    full_screening = create_report(cfg, p, comps)
    (ROOT / "results/validation/cad_assembly_clearance.json").write_text(
        json.dumps(full_screening, indent=2), encoding="utf-8"
    )
    # Keep the established per-check schema usable by the top-level validator.
    # The added acceptance record causes validation to fail on any full-pair
    # or gripper finding, even if the legacy selected structure pairs pass.
    checks.append(
        {
            "pose": "all_named_poses_and_gripper_travel",
            "parts": ["all distinct motion families"],
            "overlap_mm3": max(
                (
                    r["overlap_mm3"]
                    for v in [
                        *full_screening["poses"].values(),
                        *full_screening["gripper_openings"].values(),
                    ]
                    for r in v["interferences"]
                ),
                default=0.0,
            ),
            "result": full_screening["status"],
        }
    )
    result = {
        "status": "VERIFIED DIGITALLY",
        "cad_kernel": "build123d 0.13 / OpenCascade",
        "length_unit": "mm; source config m converted by x1000",
        "component_count": len(comps),
        "components": rows,
        "poses": pose_rows,
        "geometric_mass_total_kg": sum(r["geometric_mass_kg"] for r in rows),
        "geometric_mass_by_group_kg": {
            g: sum(r["geometric_mass_kg"] for r in rows if r["group"] == g)
            for g in ["base", "j1", "j2", "j3", "j4", "j5", "j6"]
        },
        "structure_only_mass_by_group_kg": {
            g: sum(
                r["geometric_mass_kg"]
                for r in rows
                if r["group"] == g
                and r["role"]
                in ("structure", "hollow output shaft", "linear guide", "replaceable contact pad")
            )
            for g in ["base", "j1", "j2", "j3", "j4", "j5", "j6"]
        },
        "mass_warning": "Geometric envelope/material estimate: motor/gearbox/bearing interiors are not detailed, intersecting same-group seats are summed. Dynamic lumped masses in config remain ASSUMED independently.",
        "interference_checks": checks,
        "full_pair_screening": full_screening,
        "source_sha256": full_screening["source_sha256"],
        "interference_scope": "36 legacy selected structure checks plus acceptance of all component pairs at six named poses and gripper closed/mid/open. Adjacent joints are included. Same rigid-motion families are assembled interfaces. See full_pair_screening counts and exclusions; finite screening is not an exhaustive swept proof or physical certification.",
        "gripper": {
            "opening_mm": p["opening"],
            "jaw_travel_each_mm": p["opening"] / 2,
            "finger_length_mm": p["finger_length"],
            "tool_length_mm": p["tool_length"],
        },
    }
    (ROOT / "results/validation/cad_validation.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    manifest = {
        "length_unit": "mm",
        "source": "exact Build123d BRep tessellation",
        "coordinate_convention": "local group frames base,j1..j6, chain Z Y Y X Y X",
        "components": mesh_rows,
        "pose_transforms": transform_rows,
    }
    (ROOT / "cad/exports/meshes/assembly_meshes.json").write_text(
        json.dumps(manifest, separators=(",", ":")), encoding="utf-8"
    )
    from drawings import generate_drawings

    generate_drawings(p)
    print(
        f"Generated {len(comps)} components, 6 assemblies; geometric envelope mass {result['geometric_mass_total_kg']:.3f} kg",
        flush=True,
    )
    if full_screening["status"] != "PASS":
        raise SystemExit(
            "CAD exported for inspection, but all-pair interference acceptance failed."
        )


if __name__ == "__main__":
    main()
