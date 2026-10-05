"""Refresh engineering tables and presentation from actual checked-in results."""

from pathlib import Path
import json
import tomllib

import yaml

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write(path, text):
    (ROOT / path).write_text(text.strip() + "\n", encoding="utf-8")


def update():
    c = yaml.safe_load((ROOT / "config/robot.yaml").read_text())
    torque = read("results/mechanical/joint_torque.json")
    beam = read("results/mechanical/structural.json")
    workspace = read("results/workspace/metrics.json")
    motion = read("results/trajectories/pick_place_metrics.json")
    paths = read("results/trajectories/trajectory_metrics.json")
    control = read("results/control/metrics.json")
    numeric = read("results/validation/numerical_validation.json")
    cad = read("results/validation/cad_validation.json")
    sweep = read("results/validation/cad_motion_clearance.json")
    research = read("results/research/experiments.json")
    net = read("electronics/net_verification.json")
    pcb = read("electronics/pcb_verification.json")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    validation_path = ROOT / "results/validation/validation_report.json"
    validation = (
        read("results/validation/validation_report.json") if validation_path.exists() else {}
    )
    totals = validation.get("test_totals", {})
    project_status = validation.get("project_status", "VALIDATION PENDING")
    pcb_summary = (
        "A native routed PCB, Gerber/drill outputs and independent schematic-board checks "
        "are included. Native KiCad DRC and connectivity results are retained in "
        "[PCB verification](../electronics/pcb_verification.json). "
        "DRC verifies the configured digital layout rules; physical performance remains unverified."
    )
    test_text = (
        f"{totals['tests']} tests; {totals['failures']} failures; {totals['errors']} errors"
        if totals
        else "See the executed pytest report"
    )
    grip = motion["gripper"]
    mass_table = "\n".join(
        f"| {name.replace('_', ' ').title()} | {c['mass'][name]:.2f} | ASSUMED |"
        for name in [
            "base",
            "turret",
            "upper_arm",
            "forearm",
            "wrist_roll",
            "wrist_pitch",
            "flange_gripper",
            "payload",
        ]
    )
    gear_table = "\n".join(
        f"| J{j + 1} | {torque['conservative_gravity_bound_nm'][j]:.3f} | {torque['concept_output_torque_nm'][j]:.3f} | {c['actuators']['gear_ratios'][j]} | {c['actuators']['efficiencies'][j]:.2f} | {torque['concept_motor_torque_nm'][j]:.3f} |"
        for j in range(6)
    )
    beam_table = "\n".join(
        f"| {name.replace('_', ' ').title()} | {beam[name]['bending_stress_mpa']:.3f} | {beam[name]['elastic_deflection_mm']:.5f} | {beam[name]['yield_safety_factor']:.2f} |"
        for name in ["upper_arm", "forearm", "finger"]
    )
    kpi = f"""# Project KPIs

All figures are digital. Reconstruction error is an algorithm residual, not physical accuracy or repeatability.

| Metric | Value | Evidence class | Source |
|---|---|---|---|
| Revolute DOF | 6 | VERIFIED DIGITALLY | Transform model and tests |
| Nominal shoulder-centred reach | {workspace["kinematic_max_reach_from_shoulder_m"] * 1000:.0f} mm | CALCULATED | Geometry/FK |
| Nominal TCP height at straight-up pose | {(c["geometry"]["shoulder_height"] + workspace["kinematic_max_reach_from_shoulder_m"]) * 1000:.0f} mm | CALCULATED | Geometry/FK; agrees with vertical CAD assembly |
| Payload | {c["mass"]["payload"]:.1f} kg | TARGET | Design load assumption |
| Repeatability | ±{c["targets"]["repeatability_m"] * 1000:.1f} mm | TARGET — NOT VERIFIED | No physical measurement/no compliance model |
| Manipulator mass | {torque["assumed_total_manipulator_mass_kg"]:.2f} kg | ASSUMED | Lumped load model |
| Sum of CAD envelope material volumes × density | {cad["geometric_mass_total_kg"]:.3f} kg | CALCULATED | Exterior geometry, overlaps/placeholder internals caveat |
| Maximum FK closed-form discrepancy | {numeric["independent_planar_fk_max_error_m"]:.3e} m | VERIFIED DIGITALLY | {numeric["trials"]} independent planar trials |
| Maximum FK–IK–FK position error | {numeric["ik_max_position_error_m"]:.3e} m | VERIFIED DIGITALLY | {numeric["trials"]} perturbed-seed trials |
| Maximum IK orientation error | {numeric["ik_max_orientation_error_rad"]:.3e} rad | VERIFIED DIGITALLY | SO(3) residual |
| Maximum Jacobian finite-difference discrepancy | {numeric["jacobian_max_abs_error"]:.3e} | VERIFIED DIGITALLY | World linear/angular Jacobian; units by block |
| Workspace samples | {workspace["samples"]} | SIMULATED | Seed {workspace["seed"]} |
| Convex-hull envelope volume | {workspace["convex_hull_envelope_volume_m3"]:.6f} m³ | SIMULATED — ENVELOPE ONLY | Fills inaccessible holes; not reachable volume |
| Pick/place duration | {motion["duration_s"]:.5f} s | SIMULATED | {motion["samples"]} samples |
| TCP path length | {motion["path_length_m"]:.5f} m | SIMULATED | Sum of sampled segments |
| Peak task speed / assumed limit | {motion["max_velocity_limit_fraction"]:.6f} | VERIFIED DIGITALLY AT SAMPLES | Motion report |
| Peak task acceleration / assumed limit | {motion["max_acceleration_limit_fraction"]:.6f} | VERIFIED DIGITALLY AT SAMPLES | Motion report |
| PID joint tracking overall RMSE | {control["tracking"]["overall_rmse_rad"]:.6f} rad | SIMULATED | Independent inertia/damping plants |
| Shoulder static holding torque at full extension, {c["mass"]["payload"]:.1f} kg payload | {torque["extended_gravity_torque_nm"][1]:.3f} N·m | CALCULATED | Assumed masses/COM |
| Elbow static holding torque at full extension, {c["mass"]["payload"]:.1f} kg payload | {torque["extended_gravity_torque_nm"][2]:.3f} N·m | CALCULATED | Assumed masses/COM |
| Serial TCP beam deflection estimate | {beam["serial_tcp_beam_deflection_mm"]:.5f} mm | CALCULATED | Idealized closed-section cantilevers only |
| Gripper opening / each jaw travel | {grip["opening_m"] * 1000:.0f} / {grip["travel_per_jaw_m"] * 1000:.0f} mm | VERIFIED DIGITALLY / CALCULATED | CAD gap and model |
| Gripper total normal force | {grip["target_total_normal_force_N"]:.0f} N | TARGET | {grip["target_total_normal_force_N"] / 2:.0f} N per jaw |
| Screw torque at force target | {grip["required_motor_torque_Nm"]:.6f} N·m | CALCULATED | Assumed efficiency {c["gripper"]["screw_efficiency"]:.2f} |
| Native schematic ERC violations | {net["erc_violations"]} | VERIFIED DIGITALLY | All report severities under enabled KiCad default rules; see electronics scope |
| Native PCB DRC errors / warnings / unconnected | {pcb["native_drc_errors"]} / {pcb["native_drc_warnings"]} / {pcb["unconnected_items"]} | VERIFIED DIGITALLY | Executed KiCad DRC and schematic-board checks |
| PCB footprints / copper layers | {pcb["footprint_count"]} / {pcb["copper_layers"]} | VERIFIED DIGITALLY | Native board and manufacturing exports |
| Automated tests | {test_text} | VERIFIED DIGITALLY | results/validation/pytest.xml |

PCB results are retained in [PCB verification](../electronics/pcb_verification.json). Continuous collision freedom, hardware performance and functional safety are outside the verified scope.
"""
    write("docs/kpis.md", kpi)
    write(
        "docs/03_mechanical_analysis.md",
        f"""# Mechanical calculations and actuator concept

## Load model and mass basis

The SI configuration assigns lumped drive and link masses to the frames used by CAD and FK. Each moving lump is placed at its segment midpoint; the payload is at the TCP. These are ASSUMED load properties. The separate CAD envelope sum is {cad["geometric_mass_total_kg"]:.3f} kg; simplified gearbox/bearing interiors and overlapping seats prevent treating it as a complete physical BOM. The assumed manipulator mass is {torque["assumed_total_manipulator_mass_kg"]:.2f} kg, of which {torque["moving_mass_kg"]:.2f} kg moves, excluding the payload.

| Group | kg | Status |
|---|---|---|
{mass_table}

For each COM, gravity force is F=[0,0,−mg]. External axis moment is τᵢ = aᵢ·[(pCOM−oᵢ)×F]; holding torque has the opposite sign. Summation includes downstream groups only. An independent potential-energy gradient test verifies the force/moment convention.

The {torque["sample_count"]}-pose sample uses seed {torque["seed"]}; it is not proof of a worst case. Closed-form triangle-inequality lever bounds size the conceptual actuators. Full extension gives shoulder {torque["extended_gravity_torque_nm"][1]:.3f} N·m and elbow {torque["extended_gravity_torque_nm"][2]:.3f} N·m. J1 and J6 gravity moments vanish for the assumed symmetric, centred lumps; acceleration/friction allowances still require drive torque.

## Actuator sizing

Output requirement = safety factor × (gravity bound + I·amax + b·vmax). Safety factor is {c["actuators"]["safety_factor"]:.1f}. Motor torque = output / (ratio × efficiency). The diagonal inertias/damping are ASSUMED; simultaneous extrema form a conservative conceptual envelope. These are generic digital selections, not validated commercial actuator specifications.

| Joint | Gravity bound N·m | Concept output N·m | Ratio | Efficiency | Motor N·m |
|---|---|---|---|---|---|
{gear_table}

Configured joint speeds are {" / ".join(str(value) for value in c["velocity_limits_deg_s"])} deg/s. Drive torque limits are modelling assumptions. Continuous/RMS heating, reflected inertia, acceleration coupling, backlash, brake capacity, bearing loads and fatigue require further engineering.

## Analytical stiffness and strength

This is an Euler–Bernoulli calculation, not FEA. Links are ideal clamped rectangular hollow sections. I = [b·h³−(b−2t)(h−2t)³]/12. Root stress = M·h/(2I). Tip displacement = FL³/(3EI) + MtipL²/(2EI) + wL⁴/(8EI). Upper-arm loading includes the downstream elbow moment as an end couple; serial TCP displacement includes upper-tip rotation times the remaining reach.

| Member | Bending MPa | Local tip deflection mm | Yield / nominal stress |
|---|---|---|---|
{beam_table}

Combined serial TCP beam estimate is {beam["serial_tcp_beam_deflection_mm"]:.5f} mm. The large ideal-section safety ratios are not real assembly factors of safety: covers, access windows, terminal side clevis, fasteners, bearings, gears and stress concentrations are omitted. Nominal section calculations cannot establish complete CAD stiffness or ±{c["targets"]["repeatability_m"] * 1000:.1f} mm repeatability.

## Gripper mechanism

A transverse opposed-hand screw with a {c["gripper"]["screw_lead"] * 1000:.0f} mm lead drives two guided nuts/carriages. The {grip["opening_m"] * 1000:.0f} mm opening requires {grip["travel_per_jaw_m"] * 1000:.0f} mm travel per jaw, or {grip["full_stroke_screw_revolutions"]:.2f} screw revolutions. Threads and nut/bearing preload remain conceptual in CAD.

The total normal-force target is {grip["target_total_normal_force_N"]:.0f} N, or {grip["target_total_normal_force_N"] / 2:.0f} N per jaw. Energy balance gives T = Ftotal·lead/(2πη) = {grip["required_motor_torque_Nm"]:.6f} N·m at an assumed efficiency of {c["gripper"]["screw_efficiency"]:.2f}. An assumed motor torque of {c["gripper"]["motor_torque"]:.2f} N·m gives an ideal total force of {grip["ideal_force_at_assumed_motor_torque_N"]:.3f} N. With friction coefficient μ = {c["gripper"]["friction_coefficient"]:.1f} and safety factor {c["gripper"]["grip_safety_factor"]:.0f}, the target force supports an ideal friction-only payload of {grip["friction_limited_payload_kg_with_safety_factor"]:.3f} kg. This is not a load rating: acceleration, contact pressure, object damage, guide friction, backlash and actual motor current limits are omitted.

At {c["gripper"]["finger_length"] * 1000:.0f} mm finger length and {grip["target_total_normal_force_N"] / 2:.0f} N tip force, nominal stress is {beam["finger"]["bending_stress_mpa"]:.3f} MPa and elastic deflection is {beam["finger"]["elastic_deflection_mm"]:.5f} mm. Finger length changes guide moment and stiffness; it does not change ideal screw force conversion.

Sources for the underlying formula conventions: [MIT cantilever lecture](https://www.ocw.mit.edu/courses/6-152j-micro-nano-processing-technology-fall-2005/4e555db93fbd2b7473f14100fbaadcc8_lecture13.pdf), [Thomson lead-screw engineering catalogue](https://www.thomsonlinear.com/downloads/screws/Lead_Screws_cten.pdf). Material properties are explicitly assumed in the configuration rather than certified alloy/temper values.
""",
    )
    write(
        "docs/validation_matrix.md",
        f"""# Requirement traceability

Results refer to executed digital evidence, not physical performance. The exact command report is [validation report](../results/validation/validation_report.md); [numerical trials](../results/validation/numerical_validation.json) and [CAD manifest](../results/validation/cad_validation.json) retain details.

| Requirement | Result | Evidence and scope |
|---|---|---|
| MECH-001 | PASS | {cad["component_count"]} valid BRep components; {len(cad["poses"])} assemblies, STEP reimport and actual mesh renders |
| MECH-002 | PASS | {workspace["kinematic_max_reach_from_shoulder_m"] * 1000:.0f} mm nominal reach; independent FK and CAD match |
| MECH-003 | PASS for calculation / TARGET for payload | Static gravity and conceptual actuator envelope; no load rating |
| MECH-004 | PASS for digital range / TARGET for force | {grip["opening_m"] * 1000:.0f} mm maximum jaw opening; closure tests and gripper energy calculation |
| MECH-005 | PASS for concept | Volumes, material assumptions, covers and cable bores; no production tolerances |
| KIN-001 | PASS | SE(3), known poses, independent planar discrepancy {numeric["independent_planar_fk_max_error_m"]:.3e} m |
| KIN-002 | PASS for tested cases | {numeric["trials"]} perturbed-seed FK–IK–FK trials, max position {numeric["ik_max_position_error_m"]:.3e} m; unreachable and malformed targets tested |
| KIN-003 | PASS | Finite-difference max discrepancy {numeric["jacobian_max_abs_error"]:.3e} |
| KIN-004 | PASS | Configuration/planning tests and every task joint sample |
| CTRL-001 | PASS with interpolation caveat | Analytic cubic/quintic limits; linear interior only, unbounded instantaneous start/stop acceleration |
| CTRL-002 | PASS at samples | MOVE J and MOVE L reconstruction, branch continuity and sampled derivatives |
| CTRL-003 | PASS for model | PID response/tracking saturation and antiwindup; independent inertia/damping plant only |
| ELEC-001 | PASS for schematic concept | {net["component_count"]} components, {net["connected_net_count"]} connected nets, {net["pin_assignments_checked"]} pin assignments and {net["independent_topology_checks"]} topology checks |
| ELEC-002 | PASS for digital design | Native ERC: {net["erc_violations"]} violations under enabled default rules; routed PCB, actual DRC and schematic-board connectivity checks in [PCB verification](../electronics/pcb_verification.json) |
| SIM-001 | PASS for geometric sampling | {workspace["samples"]} seeded FK samples; hull/voxel limitations explicit |
| SIM-002 | PASS for ideal task | {motion["duration_s"]:.5f} s, close/open events, home return; no contact dynamics |
| SIM-003 | PASS for required representative screening | Every component pair classified across representative CAD poses and {sweep["samples_checked"]} task samples, including {sweep["exact_brep_pair_checks"]} exact BRep intersections; continuous swept collision proof is outside this evidence |
| VAL-001 | PASS | {test_text}; details in pytest.xml |
| VAL-002 | PASS | Single executed validation workflow and artifact consistency audit |
| DOC-001 | PASS | Setup, decisions, architecture, report, figures and portable commands |
| DOC-002 | PASS | Claims vocabulary and limitations audited throughout |
| RESEARCH-001 | PASS | Five actual numerical sweeps with data/plots |
| PERF-001 | NOT VERIFIED | ±{c["targets"]["repeatability_m"] * 1000:.1f} mm repeatability remains TARGET |

Version {version}: **{project_status}** within the documented digital engineering brief. See the [scope audit](digital_scope_audit.md). Physical repeatability remains a target as requested; numerical IK residuals do not establish it.
""",
    )
    write(
        "docs/engineering_report.md",
        f"""# ASTER-6 engineering report

Version {version} · 2026-10-05 · digital engineering project

## 1. Abstract

ASTER-6 is an original six-axis industrial-arm concept with reproducible BRep CAD, numerical kinematics, motion planning, a parallel gripper, load calculations and a native conceptual KiCad interface. Its nominal shoulder-centred reach is {workspace["kinematic_max_reach_from_shoulder_m"] * 1000:.0f} mm. The {c["mass"]["payload"]:.0f} kg payload and ±{c["targets"]["repeatability_m"] * 1000:.1f} mm repeatability are design targets; neither is a tested hardware rating. The project is an educational geometric digital twin whose evidence comes from executed software.

## 2. Problem

Build a credible small manipulator without copying a commercial design or constructing hardware. Engineering depth comes from consistent geometry/transforms, actual simulation, numerical reconstruction, independent checks and documented tradeoffs. The supplied task is a simple bench pick-and-place cycle.

## 3. Requirements

The [requirements](01_requirements.md) specify six revolute joints and 600–800 mm nominal reach. The selected design has a {grip["opening_m"] * 1000:.0f} mm gripper opening and a {c["mass"]["payload"]:.0f} kg payload target. Configured speed and acceleration limits, FK/IK/Jacobian checks, reproducible motion/control experiments and evidence-linked documentation complete the digital scope. The [validation matrix](validation_matrix.md) separates verified digital checks from unverified performance targets.

## 4. Mechanical architecture

A rotating turret, shoulder clevis, hollow upper arm, elbow clevis, hollow forearm and X-Y-X wrist carry an original {c["geometry"]["tool_flange_diameter"] * 1000:.0f} mm tool flange. Six M5 clearance holes on a 46 mm pitch circle and a central pilot/adapter provide an interchangeable interface. Compatibility with a commercial flange standard is unverified. Covers, bearing seats, cable bores, guide rods and actuator envelopes give the geometry an engineering purpose.

## 5. CAD methodology

Build123d 0.13.0 creates {cad["component_count"]} valid BRep components from centralized SI inputs, converted explicitly to millimetres. The {len(cad["poses"])} configured assemblies export STEP/STL. STEP reimports preserve the reported component counts; the maximum relative volume discrepancy is {max(pose["step_volume_relative_error"] for pose in cad["poses"].values()):.3e}. CAD joint placements match the software transforms, with maximum matrix-entry discrepancy {max(pose["max_cad_fk_transform_error"] for pose in cad["poses"].values()):.3e}. FreeCAD independently imports the exports, and Blender renders their tessellated geometry. Dimension sheets describe interfaces and nominal sections; manufacturing tolerances remain open. See [CAD methodology](04_cad.md).

## 6. Kinematic model

The chain is Tz(h)Rz(q1)Ry(q2)Tx(L1)Ry(q3)Tx(L2)Rx(q4)Tx(wr)Ry(q5)Tx(wp)Rx(q6)Tx(tool). FK produces TCP pose. The world geometric Jacobian stacks axis cross TCP displacement and axis direction. Numerical least-squares IK uses bounded joints, translation scaled by reach and SO(3) logarithmic orientation residuals, plus multiple starts and residual verification. [Kinematics](02_kinematics.md) defines every frame, limit and singularity caveat.

## 7. Workspace

The {workspace["samples"]} seeded joint samples reach a maximum sampled shoulder radius of {workspace["sampled_max_radius_from_shoulder_m"]:.6f} m, compared with the {workspace["kinematic_max_reach_from_shoulder_m"] * 1000:.0f} mm nominal reach. Of these samples, {workspace["above_floor_samples"]} place the TCP above the base plane. The {workspace["convex_hull_envelope_volume_m3"]:.6f} m³ convex hull fills inaccessible holes, so it is an envelope rather than a reachable or collision-free volume. The dimensionless smallest Jacobian singular value is below 0.01 in {workspace["fraction_scaled_sigma_min_below_0_01"] * 100:.2f}% of samples. This is a geometric conditioning indicator, not a safety threshold. [Workspace plots](../results/workspace/workspace_3d.png) and raw data preserve the sampling details.

## 8. Gripper

Two guided jaws use an opposed-hand screw concept. A {grip["opening_m"] * 1000:.0f} mm opening requires {grip["travel_per_jaw_m"] * 1000:.0f} mm travel per jaw, or {grip["full_stroke_screw_revolutions"]:.2f} revolutions at a {c["gripper"]["screw_lead"] * 1000:.0f} mm lead. The {grip["target_total_normal_force_N"]:.0f} N total normal-force target requires a calculated {grip["required_motor_torque_Nm"]:.6f} N·m at assumed efficiency {c["gripper"]["screw_efficiency"]:.2f}. The ideal friction-only payload estimate is {grip["friction_limited_payload_kg_with_safety_factor"]:.3f} kg, using μ = {c["gripper"]["friction_coefficient"]:.1f} and safety factor {c["gripper"]["grip_safety_factor"]:.0f}. Contact pressure, backlash, guide friction and force control remain unmodelled. The animated object is a task token whose visual size does not establish a physical mass or density.

## 9. Mechanical calculations

The assumed manipulator mass is {torque["assumed_total_manipulator_mass_kg"]:.2f} kg; the separate summed CAD envelope/material estimate is {cad["geometric_mass_total_kg"]:.3f} kg. Midpoint COM gravity loading at full extension with a {c["mass"]["payload"]:.0f} kg payload gives shoulder holding torque of {torque["extended_gravity_torque_nm"][1]:.3f} N·m and elbow torque of {torque["extended_gravity_torque_nm"][2]:.3f} N·m. A potential-energy gradient test checks torque signs and magnitudes independently. Ideal closed-section beam calculations estimate {beam["serial_tcp_beam_deflection_mm"]:.5f} mm serial TCP deflection. Access cutouts, the terminal clevis, contacts, gearbox/bearing compliance and fatigue are omitted, so this cannot establish complete robot stiffness. [Mechanical analysis](03_mechanical_analysis.md) gives the formulas and tables.

## 10. Actuator sizing

Conceptual output requirements combine all-angle gravity lever bounds, assumed diagonal inertia/damping allowances and safety factor {c["actuators"]["safety_factor"]:.0f}. The shoulder requires {torque["concept_output_torque_nm"][1]:.3f} N·m output torque; a {c["actuators"]["gear_ratios"][1]}:1 reduction at {c["actuators"]["efficiencies"][1]:.2f} efficiency implies {torque["concept_motor_torque_nm"][1]:.3f} N·m motor torque. The elbow output requirement is {torque["concept_output_torque_nm"][2]:.3f} N·m, using {c["actuators"]["gear_ratios"][2]}:1 reduction and {c["actuators"]["efficiencies"][2]:.2f} efficiency. Commercial actuator, continuous-duty, brake, thermal and bearing ratings are unverified.

## 11. Motion planning

Joint planning provides constant-speed linear interiors, plus cubic and quintic time laws with analytic derivatives and minimum-duration checks. Linear start/stop acceleration is unbounded; quintic is the rest-to-rest default. MOVE L combines straight TCP interpolation, orientation SLERP, continuation IK and sampled uniform time scaling. The supplied vertical path has a maximum sampled lateral drift of {paths["move_l_max_xy_drift_m"]:.3e} m. Between-sample derivative limits and global collision freedom remain unverified.

## 12. Control system

Saturated PID with conditional-integration antiwindup acts on independent plants, Iq̈ + bq̇ = τ, with a {c["control"]["dt"] * 1000:.0f} ms integration step. Model parameters are assumed. Overall joint tracking RMSE for the pick/place trajectory is {control["tracking"]["overall_rmse_rad"]:.6f} rad. The configured step responses settle within 2% in {min(control["step"]["settling_time_2percent_s"]):.3f}–{max(control["step"]["settling_time_2percent_s"]):.3f} s. These simulations omit gravity, coupling, drive delays, sensor noise, backlash and physical tuning. The arm animation follows planned joints; control tracking is a separate experiment.

## 13. Electronics architecture

The native joint/sensor schematic contains {net["component_count"]} components, {net["connected_net_count"]} connected nets and {net["pin_assignments_checked"]} checked pin assignments. It covers a protected 5 V input, 3.3 V supply, external MCU header, filtered/clamped encoder and limit inputs, external-drive STEP/DIR/ENABLE signals and RS-485. Native ERC reports {net["erc_violations"]} violations under the enabled default rules, with every report severity included. The exported netlist also passes {net["independent_topology_checks"]} topology checks. {pcb_summary} [Electronics scope](05_electronics.md) documents the board, rules, assumptions and manufacturing-review limitations.

## 14. Simulation

The ideal pick/place cycle lasts {motion["duration_s"]:.5f} s, contains {motion["samples"]} joint samples and traces {motion["path_length_m"]:.5f} m of TCP path. Gripper close/open events occur during dwells, and the arm returns home. Peak sampled speed and acceleration fractions of their configured limits are {motion["max_velocity_limit_fraction"]:.6f} and {motion["max_acceleration_limit_fraction"]:.6f}. The offline [CAD twin](../simulations/aster6_twin.html) renders actual CAD meshes with the recorded joint transforms; the [FK animation](../results/trajectories/pick_place_fk.gif) shows the same mathematical motion. Browser interactions and JavaScript/Python transforms are checked separately. Grasp uses an ideal attachment, with no contact dynamics.

## 15. Verification

Automated test evidence: {test_text}. An additional {numeric["trials"]} randomly generated targets use perturbed initial joints for FK–IK–FK reconstruction. The maximum position residual is {numeric["ik_max_position_error_m"]:.3e} m and the orientation residual is {numeric["ik_max_orientation_error_rad"]:.3e} rad. The Jacobian discrepancy against finite differences is {numeric["jacobian_max_abs_error"]:.3e}; independent planar FK discrepancy is {numeric["independent_planar_fk_max_error_m"]:.3e} m. Selected structure-pair checks cover {len(cad["poses"])} CAD poses and {sweep["samples_checked"]} task positions, including {sweep["exact_brep_pair_checks"]} exact BRep pair intersections during the task. This is sampled clearance evidence. A fresh isolated wheel installation verifies packaged configuration and detached CLI execution. The evidence is retained under `results/validation`.

## 16. Results and research questions

The [KPI table](kpis.md) labels every numerical claim. Actual parameter sweeps are generated by analysis/research_experiments.py:

- RQ1: varying the upper-arm/forearm ratio at a fixed {(research["RQ1"]["values"][2]["upper_arm_m"] + research["RQ1"]["values"][2]["forearm_m"]) * 1000:.0f} mm total link length preserves outer reach while changing minimum sampled radius and above-floor voxel occupancy. At the studied ratio of {research["RQ1"]["values"][2]["ratio"]:.3f}, the minimum sampled radius is {research["RQ1"]["values"][2]["sample_min_shoulder_radius_m"] * 1000:.1f} mm in {research["RQ1"]["samples_per_ratio"]} shared samples. Occupancy is a sampling index, not reachable volume.
- RQ2: each additional payload kilogram increases shoulder static torque by {(research["RQ2"]["shoulder_nm"][1] - research["RQ2"]["shoulder_nm"][0]) / (research["RQ2"]["payload_kg"][1] - research["RQ2"]["payload_kg"][0]):.4f} N·m and elbow torque by {(research["RQ2"]["elbow_nm"][1] - research["RQ2"]["elbow_nm"][0]) / (research["RQ2"]["payload_kg"][1] - research["RQ2"]["payload_kg"][0]):.4f} N·m at full extension.
- RQ3: quintic durations {" → ".join(f"{row['duration_s']:.0f}" for row in research["RQ3"])} s produce maximum velocities {" → ".join(f"{row['max_velocity_rad_s']:.6f}" for row in research["RQ3"])} rad/s and accelerations {" → ".join(f"{row['max_acceleration_rad_s2']:.6f}" for row in research["RQ3"])} rad/s².
- RQ4: gain factors {" / ".join(f"{row['gain_scale']:g}" for row in research["RQ4"])} give J2 two-percent settling times of {" / ".join(f"{row['settling_time_2percent_s']:.3f}" for row in research["RQ4"])} s and peak commands of {" / ".join(f"{row['peak_torque_nm']:.2f}" for row in research["RQ4"])} N·m. For this plant, higher gain does not monotonically improve settling.
- RQ5: increasing finger length from {research["RQ5"]["finger_length_m"][0] * 1000:.0f} to {research["RQ5"]["finger_length_m"][-1] * 1000:.0f} mm increases nominal stress from {research["RQ5"]["stress_mpa"][0]:.0f} to {research["RQ5"]["stress_mpa"][-1]:.0f} MPa and deflection from {research["RQ5"]["deflection_mm"][0]:.5f} to {research["RQ5"]["deflection_mm"][-1]:.5f} mm at {grip["target_total_normal_force_N"] / 2:.0f} N per jaw. Ideal screw torque stays at {grip["required_motor_torque_Nm"]:.6f} N·m because force and lead are fixed.

Figures and raw data live in [research results](../results/research/experiments.json).

## 17. Limitations

No hardware, measured repeatability, certified payload, full structural FEA, fatigue assessment, collision/contact dynamics, production tolerances, functional safety or real-time firmware. Numerical IK is local and does not enumerate every solution. Workspace includes impossible/self-colliding poses. Collision checks are representative and sampled. PID is deliberately uncoupled. Material values, COMs, inertia, friction and screw efficiency are assumptions. These limitations describe the requested digital concept; physical validation is outside its scope. The executed workflow status is **{project_status}**.

## 18. Future work

Possible extensions are continuous swept paths, CAD-derived inertia tensors/coupled gravity dynamics, compliant backlash/contact/gripper modelling, detailed tolerance/fastener/bearing checks and specialist manufacturing/EMC review of the conceptual PCB. The digital-only scope remains; physical validation must not be inferred from numerical improvements.

## 19. Conclusion

The project provides a reproducible original robot concept with consistent geometry, rigid-body kinematics, executed numerical experiments, CAD exports and a routed conceptual electronics design with native checks. Its version {version} workflow reports **{project_status}**. The documented targets and simplifications preserve the distinction between digital verification and hardware performance.
""",
    )
    write(
        "README.md",
        f"""# ASTER-6 · Industrial robot arm digital twin

An original six-axis robot with parametric CAD, numerical kinematics and a reproducible pick-and-place simulation.

![ASTER-6 actual CAD assembly](cad/renders/hero.png)

**Digital only · v{version} · {project_status}**

Designed for robotics education and portfolio review. Every result is generated from source; no physical robot was built. Payload and repeatability remain design targets. The conceptual electronics include a routed PCB, manufacturing exports and native DRC; collision evidence is representative and sampled.

## See it move

Open **[the offline interactive CAD twin](simulations/aster6_twin.html)** locally: orbit, change all six joints, adjust the gripper, select poses and play the recorded task. The single HTML file needs no server or internet. GitHub displays its source; download it to open it in a browser.

![FK pick-and-place animation](results/trajectories/pick_place_fk.gif)

The {motion["duration_s"]:.2f} s task follows MOVE J and MOVE L segments: approach, grasp, lift, transport, release and return home. CAD meshes and animation use the actual transform chain. The grasp is an ideal attachment; contact physics is not simulated.

## Features and specifications

| Item | Value / evidence |
|---|---|
| Original geometry | {cad["component_count"]} valid BRep components; {len(cad["poses"])} STEP/STL assemblies |
| DOF / link lengths | Six revolute joints / {c["geometry"]["upper_arm_length"] * 1000:.0f} mm upper arm + {c["geometry"]["forearm_length"] * 1000:.0f} mm forearm |
| Nominal reach | {workspace["kinematic_max_reach_from_shoulder_m"] * 1000:.0f} mm from shoulder; nominal straight-up TCP height {(c["geometry"]["shoulder_height"] + workspace["kinematic_max_reach_from_shoulder_m"]) * 1000:.0f} mm above base |
| Payload / repeatability | {c["mass"]["payload"]:.0f} kg / ±{c["targets"]["repeatability_m"] * 1000:.1f} mm **TARGET**, physically unverified |
| Mass basis | {torque["assumed_total_manipulator_mass_kg"]:.2f} kg assumed; separate {cad["geometric_mass_total_kg"]:.3f} kg CAD envelope sum with stated limitations |
| Gripper | {grip["opening_m"] * 1000:.0f} mm opening; {grip["target_total_normal_force_N"]:.0f} N total force target; calculated screw torque {grip["required_motor_torque_Nm"]:.3f} N·m |
| FK / IK / Jacobian | Bounded numerical IK; {numeric["trials"]} perturbed-seed pose trials |
| Motion / control | Linear/cubic/quintic MOVE J, sampled MOVE L and saturated PID |
| Electronics | Native {net["component_count"]}-component KiCad interface; {net["erc_violations"]} ERC violations under enabled default rules; routed PCB/native DRC and connectivity evidence |
| Tests | {test_text} |

## Run

Python 3.12+ is required. From the organized repository root, enter the source folder (skip the `cd` if already there):

```bash
cd 06_Complete_Project_Source
python -m venv .venv
```

Activate `.venv` (`.venv\\Scripts\\Activate.ps1` on Windows; `source .venv/bin/activate` on Linux/macOS), then:

```bash
python -m pip install -e ".[cad,dev]"
python -m robotarm.demo --all
python scripts/run_validation.py
```

A fresh isolated environment validated the built wheel, its bundled configuration and a detached CLI demonstration. `requirements-lock.txt` records the dependency versions used for the generated results.

| Command | Generated evidence |
|---|---|
| `python scripts/generate_cad.py` | STEP/STL, mesh manifest, CAD checks and dimension sheets |
| `python -m robotarm.demo --workspace` | Workspace projections, 3D cloud and singularity plots |
| `python -m robotarm.demo --trajectory` | MOVE J/MOVE L and interpolation comparisons |
| `python -m robotarm.demo --pick-place` | Recorded joint data, TCP path and FK GIF |
| `python -m robotarm.demo --control` | PID step/tracking curves and errors |
| `python scripts/generate_results.py` | All numerical analyses/research and offline twin |
| `python electronics/run_checks.py` | Native KiCad ERC, PCB DRC, schematic-board/net checks and manufacturing exports |
| `python scripts/run_validation.py --full` | CAD/results regeneration followed by digital checks |

KiCad 10 is needed for native ERC and PCB DRC. Its CLI is discovered from PATH or Windows installation records; `electronics/run_checks.py` also accepts `--kicad-cli`. The validation workflow accepts `--skip-electronics` when KiCad is unavailable and records electronics as NOT VERIFIED in that run. FreeCAD and Blender support independent inspection and rendering; see [CAD methodology](docs/04_cad.md) for their commands.

## Architecture and CAD

![System architecture](docs/diagrams/system_architecture.svg)

The [single SI configuration](config/robot.yaml) drives the CAD/model/planner/analysis. Six Z-Y-Y-X-Y-X rotations orient hollow links, realistic clevis joints, access panels, cable bores, bearings and actuator envelopes. [STEP assembly](cad/exports/STEP/assembly_home.step), [drawings](docs/drawings/engineering_interfaces.pdf), [gripper render](cad/renders/gripper.png) and [CAD methodology](docs/04_cad.md) support close inspection.

## Generated results

![Workspace cloud](results/workspace/workspace_3d.png)

The workspace plot comes from {workspace["samples"]} seeded FK samples. Its {workspace["convex_hull_envelope_volume_m3"]:.4f} m³ convex hull fills inaccessible regions, so it represents an envelope rather than a collision-free reachable volume. Full extension and wrist alignment produce singularities. [Kinematics](docs/02_kinematics.md) defines the frames, equations and solver limitations.

| Result | Generated value | Meaning |
|---|---|---|
| Maximum IK position residual | {numeric["ik_max_position_error_m"]:.3e} m | Numerical reconstruction only |
| Shoulder / elbow gravity holding torque | {torque["extended_gravity_torque_nm"][1]:.2f} / {torque["extended_gravity_torque_nm"][2]:.2f} N·m | Calculated with assumed masses and {c["mass"]["payload"]:.0f} kg payload |
| Task peak velocity / acceleration fractions | {motion["max_velocity_limit_fraction"]:.4f} / {motion["max_acceleration_limit_fraction"]:.4f} | Fractions of configured limits at tested samples |
| PID tracking RMSE | {control["tracking"]["overall_rmse_rad"]:.6f} rad | Independent inertia/damping plant simulation |
| Sampled CAD task clearance | {sweep["samples_checked"]} poses / {sweep["exact_brep_pair_checks"]} exact BRep checks; maximum prohibited overlap {sweep["max_all_pair_overlap_mm3"]:g} mm³ | All component pairs classified; continuous motion not verified |

Five [research experiments](results/research/experiments.json) vary link ratio, payload, motion duration, PID gains and finger length. [Mechanical calculations](docs/03_mechanical_analysis.md), [control curves](results/control/pid_tracking.png) and [complete KPIs](docs/kpis.md) keep assumed/target/calculated/simulated/verified claims separate.

## Conceptual electronics

The native [KiCad schematic](electronics/joint_interface.kicad_sch), [PCB](electronics/joint_interface.kicad_pcb) and [schematic PDF](electronics/exports/joint_interface.pdf) cover regulated logic power, encoder/limit inputs, external-drive commands and RS-485. All {net["stock_footprints_found"]} assigned stock footprint files were found, and {net["pin_assignments_checked"]} exported pin assignments were verified. Native ERC reports {net["erc_violations"]} violations under the enabled default rules. The [PCB verification](electronics/pcb_verification.json) retains actual DRC and schematic-board checks. [Electronics scope](docs/05_electronics.md) documents fabrication outputs, rules, circuit calculations and assumptions. No physical hardware or manufacturing suitability is claimed.

## Verification, report and limitations

Read the [engineering report](docs/engineering_report.md), [validation matrix](docs/validation_matrix.md), [executed check report](results/validation/validation_report.md), [decision log](docs/design_decisions.md) and [authentic journal](docs/project_journal.md).

This is a geometric digital twin with simplified educational control. Repeatability and payload ratings have no physical verification. Full CAD structural FEA, fatigue assessment, functional safety, coupled dynamics, frictional contact, manufacturing tolerances and real drive firmware are outside the implemented educational model. Workspace sampling and IK do not enforce collision avoidance. Collision checks are representative and sampled; manual slider poses may collide. The executed status is **{project_status}** for the [documented digital scope](docs/digital_scope_audit.md).

## Best portfolio material

1. [Hero CAD render](cad/renders/hero.png) — original overall mechanical design.
2. [Interactive CAD twin](simulations/aster6_twin.html) — model-driven motion and joint controls.
3. [Gripper render](cad/renders/gripper.png) — guides, jaws and interchangeable tool interface.
4. [Engineering interface drawings](docs/drawings/engineering_interfaces.pdf) — meaningful dimensions.
5. [Coordinate frames](results/workspace/coordinate_frames.png) — explain the mathematics.
6. [Pick/place joint curves](results/trajectories/pick_place_joints.png) — motion constraints and derivatives.
7. [PID tracking](results/control/pid_tracking.png) — feedback model and measured simulation error.
8. [Payload experiment](results/research/payload.png) — connect engineering decisions to calculations.
9. [Native schematic PDF](electronics/exports/joint_interface.pdf) — real connectivity and ERC evidence.
10. [Engineering report](docs/engineering_report.md) — results, verification and honest limitations.

MIT-licensed project source. Third-party tool/library licenses remain their own; citation metadata is in CITATION.cff.
""",
    )
    return [
        "README.md",
        "docs/engineering_report.md",
        "docs/03_mechanical_analysis.md",
        "docs/kpis.md",
        "docs/validation_matrix.md",
    ]


if __name__ == "__main__":
    print("\n".join(update()))
