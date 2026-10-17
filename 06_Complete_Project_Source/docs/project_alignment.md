# Project purpose and alignment with the original brief

ASTER-6 explores one connected engineering problem: choose an original robot
geometry, use the same geometry to plan a useful tool motion, estimate its loads
and gripper requirements, and demonstrate feedback control in a reproducible
digital model. The intended result is a credible student engineering project
that a professor or reviewer can inspect, run and question.

The design is a six-revolute-axis arm with an interchangeable parallel gripper.
Its nominal shoulder-centred reach is 790 mm, its assumed payload target is
4 kg, its repeatability target is ±0.1 mm and its jaw opening is 90 mm. These
choices sit within the ranges in the original brief. The design is original;
commercial robot compatibility and physically measured performance are not
claimed.

## Follow one demonstration through the engineering

1. Inspect the [CAD component catalog](component_catalog.md),
   [dimensioned interfaces](drawings/engineering_interfaces.pdf) and six poses.
   The mounting, joint, tool and gripper interfaces explain how the geometry
   supports the proposed mechanism.
2. Read the [frame and kinematic formulation](02_kinematics.md). The central
   [SI parameters](../config/robot.yaml) drive the transform chain and CAD
   dimensions. The browser viewer uses meshes from those actual solids.
3. Run the [pick-and-place task](../simulations/aster6_twin.html). MOVE J handles
   joint transfers, regular approximate MOVE L segments handle approach and
   retreat, and the gripper sequences a rigid ideal attachment. Position and
   orientation follow the mathematical tool pose.
4. Compare [loads, structure and actuator sizing](03_mechanical_analysis.md)
   with the [PID model](architecture.md) and the [five parameter studies](../results/research/experiments.json).
   The studies explain effects and tradeoffs using generated data.
5. Inspect the [electronics architecture](05_electronics.md),
   [component/BOM guide](electronics_components.md), native schematic, routed
   PCB and actual check reports. This is the low-voltage joint/sensor interface
   portion of the hypothetical controller architecture.
6. Read the [executed validation](../results/validation/validation_report.md)
   and [requirements matrix](validation_matrix.md). Their scope, source
   bindings and failure conditions matter as much as the illustrations.

## Original goals and their concrete project form

| Original brief | Project form | Where to assess it |
|---|---|---|
| Original, realistic six-axis mechanical design and interchangeable gripper | Reproducible Build123d solids, native FreeCAD assembly, STEP/STL parts, joint frames, guides, mounting and service interfaces | [CAD methodology](04_cad.md), [catalog](component_catalog.md), drawings and native model |
| Engineering reasons for dimensions and choices | Central specification, original flange, lumped mass assumptions, opposed-screw gripper and explicit tradeoffs | [Requirements](01_requirements.md), [decisions](design_decisions.md), [mechanics](03_mechanical_analysis.md) |
| Correct mathematics and model-driven motion | FK, bounded numerical IK, Jacobian, seeded workspace, constrained planning and recorded task | [Theory guide](theory_guide.md), kinematics, trajectory data and browser checks |
| Simplified digital feedback control | Saturated PID with antiwindup and independent inertia/damping plants; step and tracking errors | [Architecture](architecture.md), [control evidence](../results/control/metrics.json) |
| Meaningful conceptual electronics | Regulated logic supply, encoder/limit inputs, external-drive command interface, RS-485, native PCB and manufacturing exports | [Electrical chapter](05_electronics.md), [native PCB evidence](../electronics/pcb_verification.json) |
| Educational/research value | Link-ratio, payload, duration, controller-gain and finger-length sweeps | [Experiments](../results/research/experiments.json), [KPIs](kpis.md), engineering report |
| Reproducible, tested and organized delivery | Installable package, regression tests, native checks, source-bound reports, numbered folders and offline viewing | [Setup](../README.md#run), [completion checklist](completion_checklist.md), validation and organization manifests |
| A credible engineering portfolio with an authentic process | Clear README, drawings, actual CAD renders, demonstrations, assumptions, decisions and recorded corrections | [Engineering report](engineering_report.md), [journal](project_journal.md), Git history and releases |

## Completion means the documented digital brief

For the ordinary demonstration, follow the [source README](../README.md#run).
`python scripts/run_validation.py --full` additionally rebuilds the primary
CAD and numerical outputs, then refreshes native FreeCAD, Blender, drawings/render
composition and sampled clearance before checking the full project. It requires
installed FreeCADCmd, Blender and KiCad alongside the Python dependencies.
Tool-path overrides are documented in [CAD reproduction](04_cad.md#refresh-native-cad-evidence)
and [electronics reproduction](05_electronics.md#reproduce-the-evidence).
Fresh browser and isolated-wheel evidence are required whenever their bound
artifact or package sources change; the validator rejects stale evidence.

The original request explicitly excludes physical construction. It permits
analytical beams and simplified joint plants, and asks for representative
interference screening and a meaningful conceptual controller subsection.
Accordingly, the implemented scope includes these models with stated limits.
Hardware payload/repeatability, fatigue, EMC, functional safety, complete
manufacturing tolerances, production firmware, frictional grasp physics and
continuous swept collision certification remain unverified.

The current status must come from [executed checks](../results/validation/validation_report.json)
that match the current sources. The [final review](final_review.md) records
defects found and corrected, while the [scope audit](digital_scope_audit.md)
maps the detailed brief to evidence. A declaration of completion does not replace
those checks or turn assumptions into measured performance.
