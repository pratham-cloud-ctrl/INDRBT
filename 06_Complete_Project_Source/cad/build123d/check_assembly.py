"""All-component interference screening at the six named CAD configurations.

Components in one rigid assembly may share material at modeled attachment
interfaces. The two gripper jaws are separate moving families, even though their
robot joint frame is the same. No adjacent robot-joint pair is blanket-excluded.
"""

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

from assembly import group_transforms, location
from geometry import build_components
from parameters import ROOT, parameters


def rigid_family(component):
    """Identify bodies sharing one motion; keep jaw travel separate from J6."""
    jaw_parts = ("gripper_jaw_carriage_", "gripper_finger_", "gripper_contact_pad_")
    if component.name.startswith(jaw_parts):
        return "j6_jaw_positive" if component.name.endswith("+1") else "j6_jaw_negative"
    return component.group


def assess(components, q_deg, parameters_mm):
    """Conservative AABB rejection followed by exact OpenCascade common volume."""
    transforms = group_transforms(q_deg, parameters_mm)
    shapes = [c.shape.moved(location(transforms[c.group])) for c in components]
    bounds = [s.bounding_box() for s in shapes]
    minima = np.array([list(b.min) for b in bounds])
    maxima = np.array([list(b.max) for b in bounds])
    families = [rigid_family(c) for c in components]
    records = []
    rejected = tested = excluded = 0
    for i, j in itertools.combinations(range(len(components)), 2):
        if families[i] == families[j]:
            excluded += 1
            continue
        # Positive interior overlap in all dimensions is necessary for a
        # positive-volume intersection. Exact or tolerance-level contacts are
        # not regarded as penetration.
        depth = np.minimum(maxima[i], maxima[j]) - np.maximum(minima[i], minima[j])
        if np.any(depth <= 1e-6):
            rejected += 1
            continue
        tested += 1
        common = shapes[i] & shapes[j]
        volume = float(common.volume) if common else 0.0
        if volume > 1e-3:
            records.append(
                {
                    "parts": [components[i].name, components[j].name],
                    "motion_families": [families[i], families[j]],
                    "overlap_mm3": volume,
                }
            )
    return {
        "status": "PASS" if not records else "FAIL",
        "component_pairs": len(components) * (len(components) - 1) // 2,
        "same_rigid_family_pairs_excluded": excluded,
        "aabb_disjoint_pairs": rejected,
        "exact_brep_pair_checks": tested,
        "moving_geometry_min_z_mm": min(
            float(minima[i, 2]) for i, c in enumerate(components) if c.group != "base"
        ),
        "interferences": records,
    }


def source_hashes():
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [ROOT / "config/robot.yaml", Path(__file__).with_name("geometry.py")]
    }


def create_report(cfg, p, parts=None):
    """Audit source solids, optionally sharing those just exported by CAD."""
    parts = build_components(p) if parts is None else parts
    poses = {name: assess(parts, q, p) for name, q in cfg["poses_deg"].items()}
    # Jaw extremes and midpoint require independent local interference checks,
    # because group J6 alone does not encode the internal prismatic motion.
    grip = {}
    for gap in (0.0, p["opening"] / 2, p["opening"]):
        all_parts = parts if gap == p["opening"] else build_components(p, opening=gap)
        gripper = [c for c in all_parts if c.group == "j6"]
        grip[f"{gap:g}_mm"] = assess(gripper, cfg["home_deg"], p)
    return {
        "status": "PASS"
        if all(v["status"] == "PASS" for v in [*poses.values(), *grip.values()])
        else "FAIL",
        "source_sha256": source_hashes(),
        "component_count": len(parts),
        "poses": poses,
        "gripper_openings": grip,
        "all_component_pose_pair_classifications": sum(
            v["component_pairs"] for v in poses.values()
        ),
        "exact_brep_pair_checks": sum(
            v["exact_brep_pair_checks"] for v in [*poses.values(), *grip.values()]
        ),
        "scope": "Every component pair at all six named poses, plus gripper closed/mid/open. Same rigid-motion families are excluded as assembled interfaces; no adjacent robot joint is excluded wholesale. All other pairs receive conservative AABB rejection or exact BRep common-volume testing. Finite pose screening does not certify all configurations, continuous motion, tolerance/preload, or physical safety.",
        "penetration_threshold_mm3": 1e-3,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="cad_assembly_clearance.json")
    args = parser.parse_args()
    cfg, p = parameters()
    report = create_report(cfg, p)
    folder = ROOT / "results/validation"
    folder.mkdir(exist_ok=True)
    (folder / args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
