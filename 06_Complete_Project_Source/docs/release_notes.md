# ASTER-6 v1.0.0 — digital engineering release

ASTER-6 completes the documented digital educational project: an original six-axis robot and parallel gripper with reproducible CAD, numerical motion/control, engineering calculations and a routed conceptual joint/sensor PCB. No physical robot or electronics were built. Publication follows successful integrated validation and the repository audit.

- CAD: original six-axis design, 54 parametric components, STEP/STL assemblies, native FreeCAD assembly, actual renders and three interface drawing pages.
- Gripper: symmetric guide/carriage motion, opposed screw concept, 90 mm measured digital gap, calculations for travel and 200 N target force.
- Kinematics: explicit rigid transform chain, FK, bounded numerical IK, Jacobian and independent numerical checks.
- Simulation: seeded workspace/singularities, MOVE J/MOVE L, recorded pick/place, offline interactive CAD twin and FK animation.
- Control: saturated PID, antiwindup, inertia/damping plants, step and tracking metrics.
- Electronics: native 100 × 100 mm four-layer joint/sensor PCB, 44 schematic components plus four mechanical mounts, 265 track segments, 32 vias, two filled planes, 28 connected nets and 118 checked interface pins. Native enabled-rule ERC/DRC, unconnected-item and schematic-parity counts are all zero.
- Manufacturing exports: ten Gerber layers, separate PTH/NPTH drills and maps, applicable component positions, IPC-D-356, BOM, fabrication ZIP and six-page layer PDF.
- Verification: all 33 automated tests passed, alongside randomized reconstruction/Jacobian checks, CAD round trips and corrected shoulder/wrist/gripper interfaces. Six poses classify 8,586 pairs; 75 task configurations classify 107,325 pairs with 5,935 exact intersections and no prohibited overlap. The version 1.0.0 wheel was installed and exercised in a fresh isolated environment with detached imports and actual CLI output.
- Organization/documentation: numbered CAD/simulation/report/electronics/reference/source folders, browser-readable guide/reports, portable explicit app launchers, source/generated copy hashes, exact-byte checkout rules, requirements, traceability, KPIs and authentic failure/fix journal.

The [executed validation](../results/validation/validation_report.md), [PCB evidence](../electronics/pcb_verification.json), [requirements matrix](validation_matrix.md) and [scope audit](digital_scope_audit.md) define acceptance. Physical payload/repeatability, EMC, functional safety, manufacturer CAM approval, complete tolerances and continuous swept collision certification are outside the verified digital scope. Five KiCad factory-disabled DRC checks and the generic F1 footprint-filter exception are explicitly disclosed; no custom severity suppression or DRC exclusions were added.

Release assets are the complete organized project ZIP and installable Python wheel. The private repository retains the authentic earlier preview history.
