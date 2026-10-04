# Prepared handover notes — ASTER-6 0.9.0

An engineering preview is prepared. A v1.0.0 GitHub release has **not** been created because the master brief's remaining digital engineering scope is unresolved.

- CAD: original six-axis design, 54 parametric components, STEP/STL assemblies, native FreeCAD assembly, actual renders and three interface drawing pages.
- Gripper: symmetric guide/carriage motion, opposed screw concept, 90 mm measured digital gap, calculations for travel and 200 N target force.
- Kinematics: explicit rigid transform chain, FK, bounded numerical IK, Jacobian and independent numerical checks.
- Simulation: seeded workspace/singularities, MOVE J/MOVE L, recorded pick/place, offline interactive CAD twin and FK animation.
- Control: saturated PID, antiwindup, inertia/damping plants, step and tracking metrics.
- Electronics: native KiCad low-voltage joint interface, BOM, net contracts/topology review and executed full-severity ERC of enabled default rules.
- Verification: automated tests, randomized reconstruction/Jacobian checks, CAD round trips, discrete clearance screening, clean-wheel installation and browser QA.
- Documentation: requirements, traceability, report, KPIs, design choices, real failure/fix journal and exact reproduction commands.

Open work: routed PCB/native DRC, comprehensive continuous collision analysis and more complete structural/dynamic/contact models. Performance targets remain unverified physically. No hardware-ready release is claimed.
