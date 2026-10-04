"""Discrete CAD clearance checks on the actual pick/place FK trajectory."""

import hashlib
import json
import numpy as np
from parameters import ROOT, parameters
from geometry import build_components
from assembly import group_transforms, location


def main():
    cfg, p = parameters()
    cs = build_components(p)
    byname = {c.name: c for c in cs}
    source = ROOT / "results/trajectories/pick_place_samples.json"
    data = json.loads(source.read_text())
    mesh = json.loads((ROOT / "cad/exports/meshes/assembly_meshes.json").read_text())
    indices = np.unique(np.linspace(0, len(data["q_rad"]) - 1, 65).round().astype(int))
    pairs = [
        ("base_mounting_plate", "upper_arm_hollow_link"),
        ("base_mounting_plate", "forearm_hollow_link"),
        ("fixed_base_riser", "forearm_hollow_link"),
        ("upper_arm_hollow_link", "forearm_hollow_link"),
        ("upper_arm_hollow_link", "gripper_pocketed_body"),
        ("shoulder_fork_+1", "forearm_hollow_link"),
    ]
    errors = []
    min_ground = 1e9
    max_overlap = 0
    records = []
    for idx in indices:
        Ts = group_transforms(np.rad2deg(data["q_rad"][idx]), p)
        moving_min = 1e9
        for c in mesh["components"]:
            if c["group"] == "base":
                continue
            v = np.asarray(c["vertices"])
            T = Ts[c["group"]]
            z = v @ T[2, :3] + T[2, 3]
            moving_min = min(moving_min, float(z.min()))
        min_ground = min(min_ground, moving_min)
        if moving_min < -1e-3:
            errors.append(
                {"sample": int(idx), "type": "ground penetration", "min_z_mm": moving_min}
            )
        worst = 0
        for a, b in pairs:
            A = byname[a]
            B = byname[b]
            common = A.shape.moved(location(Ts[A.group])) & B.shape.moved(location(Ts[B.group]))
            vol = common.volume if common else 0
            worst = max(worst, vol)
            max_overlap = max(max_overlap, vol)
            if vol > 1e-3:
                errors.append(
                    {
                        "sample": int(idx),
                        "type": "interference",
                        "parts": [a, b],
                        "overlap_mm3": vol,
                    }
                )
        records.append(
            {
                "sample": int(idx),
                "time_s": data["t_s"][idx],
                "moving_geometry_min_z_mm": moving_min,
                "max_selected_pair_overlap_mm3": worst,
            }
        )
    report = {
        "status": "PASS" if not errors else "FAIL",
        "trajectory_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "samples_checked": len(indices),
        "trajectory_samples": len(data["q_rad"]),
        "exact_brep_pair_checks": len(indices) * len(pairs),
        "minimum_moving_geometry_height_mm": min_ground,
        "max_selected_pair_overlap_mm3": max_overlap,
        "failures": errors,
        "samples": records,
        "scope": "Discrete 65-sample CAD review, 6 selected structure pairs per sample; ground test all moving mesh vertices at 0.5-mm tessellation. Adjacent bearing fits/envelopes excluded. Not a continuous swept collision proof or environment collision plan.",
    }
    (ROOT / "results/validation/cad_motion_clearance.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k not in ("samples",)}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
