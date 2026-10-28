# INDRBT v1.2.0 — original goals, repaired mechanics and rigorous validation

INDRBT connects an original six-axis arm and interchangeable parallel gripper
to kinematics, motion planning, analytical mechanics, simplified feedback control
and a routed conceptual joint/sensor interface. The 17 October review revisited
the original digital brief and fixed defects beyond the earlier passing checks.
No physical robot or electronics were built.

- Mechanical interfaces: wider tool adapter with retained bolt ligaments, a real locating pilot and matching rear fasteners; connected nut/carriage bridges and finger supports; a nonintersecting top service hatch; actual 7 mm counterbores. The design still contains 54 parts and retains the original SI dimensions and 90 mm opening.
- Native CAD access: all 54 named FreeCAD solids open visibly. STEP/STL, native FreeCAD/Blender, actual renders and three drawing pages were regenerated. New refresh/review scripts execute native applications and require current source/artifact proof.
- Numerical behavior: reject nonfinite/nonphysical inputs, malformed rigid poses and trajectories, segment discontinuities and singular MOVE L continuation. PID, beam zero/signed-load and payload edge cases have explicit regressions.
- Actuator sizing: distinguish educational controller inertia from mass-consistent sizing inertia. A separate kinetic-energy regression checks the point-COM bounds. Coupled rigid-body dynamics remain outside this model.
- Demonstration: ideal grasp attachment now follows the complete TCP position and orientation. All 54 components remain individually inspectable in the offline browser viewer.
- Electronics: include quiescent-current heat in the regulator estimate and reject stale native PCB reports after routing/design changes. The original board/schematic geometry is unchanged. Current native ERC/DRC/connectivity/parity and manufacturing export audits pass within their enabled-rule scope.
- Reproducibility: enforce measured numerical acceptance limits, reject nonfinite saved evidence, bind validation to 76 current source/input files, compare all 15 wheel modules with source and use fresh CLI output directories. The new project-purpose guide explains how each subsystem answers the original engineering question.

## Executed verification

The complete CAD/results/native regeneration passed. The latest integrated
validation passed **91 automated tests**,
with zero failures, errors or skips, and all named integration gates.
All 54 STEP/STL component pairs and six assemblies agree with native data; all saved
FreeCAD parts are visible. Six named poses and closed/mid/open gripper checks use
312 exact intersections. The task review screens 75 configurations with 107,325
pair classifications and 6,126 exact intersections, with zero prohibited overlap.
The CAD geometric envelope/material sum is 19.907949 kg;
the separate assumed load model is 23.65 kg.

The unchanged nominal task contains 1,041 samples and lasts 9.243979567 s.
Its peak velocity/acceleration fractions are 0.951694 and 0.997971.
The ideal serial beam estimate remains 0.104075 mm. These are generated digital
results, rather than physical performance measurements.

See the [original goals](project_alignment.md), [current independent review](final_review.md),
[executed validation](../results/validation/validation_report.md),
[CAD proof](../results/validation/cad_release_consistency.json),
[theory review](../results/validation/final_theory_review.json) and
[electronics evidence](../electronics/pcb_verification.json).

Physical payload/repeatability, production tolerances, EMC, thermal qualification,
functional safety, detailed thread/preload/contact physics, complete coupled
dynamics and continuous swept collision certification remain unverified. Five
KiCad factory-disabled DRC checks remain disclosed; no custom suppression or
exclusions were added. This is a completed digital educational engineering project
within the [documented scope](digital_scope_audit.md).

Release assets are the complete organized ZIP and installable Python wheel.
At the v1.2.0 publication the repository was private and retained the authentic earlier history. On 21 October 2026 the owner explicitly requested public repository access; the separate inspection release distributes public CAD/PCB packs while preserving this engineering release.
