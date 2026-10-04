"""Analytical hollow-beam and gripper-finger elastic estimates in SI."""

from __future__ import annotations

import json
from pathlib import Path

from robotarm.config import load_config

ROOT = Path(__file__).resolve().parents[1]


def hollow_section(width: float, depth: float, wall: float) -> float:
    if not 0 < 2 * wall < min(width, depth):
        raise ValueError("Wall leaves no hollow section")
    return (width * depth**3 - (width - 2 * wall) * (depth - 2 * wall)**3) / 12


def beam_response(length: float, inertia: float, depth: float, young: float,
                  end_force: float, end_moment: float, distributed_load: float,
                  yield_strength: float):
    moment = end_force * length + end_moment + distributed_load * length**2 / 2
    stress = moment * depth / (2 * inertia)
    deflection = (end_force * length**3 / 3 + end_moment * length**2 / 2
                  + distributed_load * length**4 / 8) / (young * inertia)
    return {"root_moment_nm": moment, "bending_stress_mpa": stress / 1e6,
            "elastic_deflection_mm": deflection * 1000, "yield_safety_factor": yield_strength / stress,
            "second_moment_m4": inertia}


def run_analysis():
    c = load_config()
    g, m, material = c["geometry"], c["mass"], c["materials"]["aluminum"]
    grav = c["targets"]["gravity"]
    l1, l2, wr, wp, tool = [g[k] for k in ("upper_arm_length", "forearm_length",
                                        "wrist_roll_length", "wrist_pitch_length", "tool_length")]
    distal = m["wrist_roll"] + m["wrist_pitch"] + m["flange_gripper"] + m["payload"]
    fore_tip_couple = grav * (m["wrist_roll"] * wr / 2 + m["wrist_pitch"] * (wr + wp / 2)
                             + m["flange_gripper"] * (wr + wp + tool / 2)
                             + m["payload"] * (wr + wp + tool))
    fore_i = hollow_section(g["forearm_width"], g["forearm_depth"], g["wall_thickness"])
    fore = beam_response(l2, fore_i, g["forearm_depth"], material["young_modulus"],
                         distal * grav, fore_tip_couple, m["forearm"] * grav / l2,
                         material["yield_strength"])
    upper_i = hollow_section(g["upper_arm_width"], g["upper_arm_depth"], g["wall_thickness"])
    upper = beam_response(l1, upper_i, g["upper_arm_depth"], material["young_modulus"],
                          (distal + m["forearm"]) * grav, fore["root_moment_nm"],
                          m["upper_arm"] * grav / l1, material["yield_strength"])
    grip = c["gripper"]
    finger_i = grip["finger_width"] * grip["finger_thickness"]**3 / 12
    finger = beam_response(grip["finger_length"], finger_i, grip["finger_thickness"],
                           material["young_modulus"], grip["total_normal_force_target"] / 2,
                           0, 0, material["yield_strength"])
    # Serial deflection estimate includes upper tip rotation acting on distal reach.
    f1 = (distal + m["forearm"]) * grav
    w1 = m["upper_arm"] * grav / l1
    upper_slope = (f1 * l1**2 / 2 + fore["root_moment_nm"] * l1 + w1 * l1**3 / 6) / (material["young_modulus"] * upper_i)
    tcp_estimate = upper["elastic_deflection_mm"] + fore["elastic_deflection_mm"] + upper_slope * (l2 + wr + wp + tool) * 1000
    result = {"status": "CALCULATED linear-elastic cantilever model, not FEA",
              "upper_arm": upper, "forearm": fore, "finger": finger,
              "serial_tcp_beam_deflection_mm": tcp_estimate,
              "limitations": "Ideal clamped rectangular beams; no holes, welds, fastener contact, bearing/gear compliance, local stress, fatigue, shear deformation, transverse coupling or physical confirmation. Static deflection is not repeatability."}
    out = ROOT / "results" / "mechanical"
    out.mkdir(parents=True, exist_ok=True)
    (out / "structural.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(run_analysis(), indent=2))
