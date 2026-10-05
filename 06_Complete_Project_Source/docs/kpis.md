# Project KPIs

All figures are digital. Reconstruction error is an algorithm residual, not physical accuracy or repeatability.

| Metric | Value | Evidence class | Source |
|---|---|---|---|
| Revolute DOF | 6 | VERIFIED DIGITALLY | Transform model and tests |
| Nominal shoulder-centred reach | 790 mm | CALCULATED | Geometry/FK |
| Nominal TCP height at straight-up pose | 980 mm | CALCULATED | Geometry/FK; agrees with vertical CAD assembly |
| Payload | 4.0 kg | TARGET | Design load assumption |
| Repeatability | ±0.1 mm | TARGET — NOT VERIFIED | No physical measurement/no compliance model |
| Manipulator mass | 23.65 kg | ASSUMED | Lumped load model |
| Sum of CAD envelope material volumes × density | 19.952 kg | CALCULATED | Exterior geometry, overlaps/placeholder internals caveat |
| Maximum FK closed-form discrepancy | 2.544e-16 m | VERIFIED DIGITALLY | 60 independent planar trials |
| Maximum FK–IK–FK position error | 2.700e-11 m | VERIFIED DIGITALLY | 60 perturbed-seed trials |
| Maximum IK orientation error | 6.504e-12 rad | VERIFIED DIGITALLY | SO(3) residual |
| Maximum Jacobian finite-difference discrepancy | 2.517e-10 | VERIFIED DIGITALLY | World linear/angular Jacobian; units by block |
| Workspace samples | 6000 | SIMULATED | Seed 260105 |
| Convex-hull envelope volume | 1.902506 m³ | SIMULATED — ENVELOPE ONLY | Fills inaccessible holes; not reachable volume |
| Pick/place duration | 9.24398 s | SIMULATED | 1041 samples |
| TCP path length | 1.32360 m | SIMULATED | Sum of sampled segments |
| Peak task speed / assumed limit | 0.951694 | VERIFIED DIGITALLY AT SAMPLES | Motion report |
| Peak task acceleration / assumed limit | 0.997971 | VERIFIED DIGITALLY AT SAMPLES | Motion report |
| PID joint tracking overall RMSE | 0.006383 rad | SIMULATED | Independent inertia/damping plants |
| Shoulder static holding torque at full extension, 4.0 kg payload | 70.165 N·m | CALCULATED | Assumed masses/COM |
| Elbow static holding torque at full extension, 4.0 kg payload | 31.880 N·m | CALCULATED | Assumed masses/COM |
| Serial TCP beam deflection estimate | 0.10408 mm | CALCULATED | Idealized closed-section cantilevers only |
| Gripper opening / each jaw travel | 90 / 45 mm | VERIFIED DIGITALLY / CALCULATED | CAD gap and model |
| Gripper total normal force | 200 N | TARGET | 100 N per jaw |
| Screw torque at force target | 0.363783 N·m | CALCULATED | Assumed efficiency 0.35 |
| Native schematic ERC violations | 0 | VERIFIED DIGITALLY | All report severities under enabled KiCad default rules; see electronics scope |
| Native PCB DRC errors / warnings / unconnected | 0 / 0 / 0 | VERIFIED DIGITALLY | Executed KiCad DRC and schematic-board checks |
| PCB footprints / copper layers | 48 / 4 | VERIFIED DIGITALLY | Native board and manufacturing exports |
| Automated tests | 34 tests; 0 failures; 0 errors | VERIFIED DIGITALLY | results/validation/pytest.xml |

PCB results are retained in [PCB verification](../electronics/pcb_verification.json). Continuous collision freedom, hardware performance and functional safety are outside the verified scope.
