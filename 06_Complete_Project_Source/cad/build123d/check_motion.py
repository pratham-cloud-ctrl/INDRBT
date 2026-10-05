"""All-component discrete CAD screening of the actual pick/place trajectory."""

import hashlib
import json

import numpy as np

from check_assembly import assess, source_hashes
from geometry import build_components
from parameters import ROOT, parameters


def main():
    cfg, p = parameters()
    source = ROOT / "results/trajectories/pick_place_samples.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    times = np.asarray(data["t_s"])
    indices = set(np.linspace(0, len(times) - 1, 65).round().astype(int).tolist())
    # Include each task phase boundary and gripper event in addition to the
    # uniform samples; these are the configurations most relevant to the task.
    for phase in data["phases"]:
        for time in (phase["start_s"], phase["end_s"]):
            indices.add(int(np.argmin(np.abs(times - time))))
    for event in data["events"]:
        indices.add(int(np.argmin(np.abs(times - event["time_s"]))))
    openings = {float(p["opening"])}
    openings.update(float(e["opening_m"]) * 1000 for e in data["events"])
    parts = {gap: build_components(p, opening=gap) for gap in openings}
    records = []
    failures = []
    ground_min = float("inf")
    pair_count = exact_count = broad_count = excluded_count = 0
    for index in sorted(indices):
        time = float(times[index])
        gap = float(p["opening"])
        for event in data["events"]:
            if time >= event["time_s"]:
                gap = float(event["opening_m"]) * 1000
        result = assess(parts[gap], np.rad2deg(data["q_rad"][index]), p)
        height = result["moving_geometry_min_z_mm"]
        ground_min = min(ground_min, height)
        pair_count += result["component_pairs"]
        exact_count += result["exact_brep_pair_checks"]
        broad_count += result["aabb_disjoint_pairs"]
        excluded_count += result["same_rigid_family_pairs_excluded"]
        for interference in result["interferences"]:
            failures.append(
                {"sample": index, "time_s": time, "type": "interference", **interference}
            )
        if height < -1e-3:
            failures.append(
                {"sample": index, "time_s": time, "type": "ground penetration", "min_z_mm": height}
            )
        records.append(
            {
                "sample": index,
                "time_s": time,
                "gripper_opening_mm": gap,
                "moving_geometry_min_z_mm": height,
                "component_pairs_classified": result["component_pairs"],
                "exact_brep_pair_checks": result["exact_brep_pair_checks"],
                "max_selected_pair_overlap_mm3": max(
                    (r["overlap_mm3"] for r in result["interferences"]), default=0.0
                ),
            }
        )
        print(f"CAD trajectory sample {index}/{len(times) - 1}: {result['status']}", flush=True)
    maximum = max((r.get("overlap_mm3", 0) for r in failures), default=0.0)
    report = {
        "status": "PASS" if not failures else "FAIL",
        "trajectory_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_sha256": source_hashes(),
        "samples_checked": len(indices),
        "trajectory_samples": len(times),
        "all_component_pair_classifications": pair_count,
        "aabb_disjoint_pairs": broad_count,
        "same_rigid_family_pairs_excluded": excluded_count,
        "exact_brep_pair_checks": exact_count,
        "minimum_moving_geometry_height_mm": ground_min,
        "max_selected_pair_overlap_mm3": maximum,
        "max_all_pair_overlap_mm3": maximum,
        "failures": failures,
        "samples": records,
        "scope": "65 uniform samples plus every phase boundary and gripper event; every component pair is classified. Adjacent joints are included, and each moving jaw is distinct from the gripper body. Disjoint AABBs reject impossible intersections; all remaining pairs use exact BRep common volume. Ground height uses transformed BRep bounding boxes. Gripper event openings are checked, with additional closed/mid/open checks in cad_assembly_clearance.json. This finite task screening is not a continuous swept proof, validation of every joint-limit combination, or physical safety certification.",
    }
    (ROOT / "results/validation/cad_motion_clearance.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(
        json.dumps({k: v for k, v in report.items() if k not in ("samples",)}, indent=2), flush=True
    )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
