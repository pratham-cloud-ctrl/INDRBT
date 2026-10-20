# ASTER-6 · Engineering and theory

**[Open the public design library](https://aster-six-engineering-showcase.warmkiwi64.chatgpt.site/#guides)** — no CAD application or GitHub access required.

**Understand the design. Follow the evidence. Reproduce the results.**

ASTER-6 is an original six-axis digital robot with a parallel-jaw gripper. This library connects its CAD, mathematics, motion, load calculations, feedback control and conceptual electronics. The design's 790 mm reach is calculated; 4 kg payload and ±0.1 mm repeatability remain targets. No physical robot was built.

[Project home](../../README.md) · [Engineering walkthrough](engineering_walkthrough.md) · [Full theory guide](theory_guide.md) · [Engineering report](engineering_report.md)

![Six representative CAD configurations of the ASTER-6 robot](../cad/renders/poses.png)

## Start with one connected story

1. **[Purpose and original goals](project_alignment.md)** — what the project sets out to demonstrate and how its parts connect.
2. **[How ASTER-6 works](engineering_walkthrough.md)** — a visual introduction following one task from geometry to electronics; each plot explains what its evidence means.
3. **[Understanding the theory](theory_guide.md)** — units, transforms, IK, Jacobian, planning, loads, gripper work balance and control, with equations and interpretation.
4. **[Engineering report](engineering_report.md)** — the complete design argument, results, research findings and stated limitations.
5. **[Validation matrix](validation_matrix.md)** — trace each requirement to an executed check, then inspect the [recorded validation](../results/validation/validation_report.md).

## Find a subject

| Subject | Read first | Inspect the actual work |
|---|---|---|
| Purpose and requirements | [Project alignment](project_alignment.md), [requirements](01_requirements.md) | [Central SI parameters](../config/robot.yaml), [scope audit](digital_scope_audit.md) |
| System architecture | [Architecture](architecture.md) | [Control/data-flow diagram](diagrams/system_architecture.svg), [electronics diagram](diagrams/electronics_architecture.svg) |
| Mechanical design and CAD | [CAD methodology and reproduction](04_cad.md), [component catalog](component_catalog.md) | [Dimensioned interfaces](drawings/engineering_interfaces.pdf), [CAD source](../cad/build123d), [STEP files](../cad/exports/STEP) |
| Frames, FK, IK and Jacobian | [Kinematic formulation](02_kinematics.md) | [Kinematics source](../src/robotarm/kinematics/model.py), [numerical verification](../results/validation/numerical_validation.json) |
| Workspace and singularities | [Walkthrough: kinematics](engineering_walkthrough.md#2-kinematics-turns-geometry-into-a-tool-pose) | [Workspace plots/data](../results/workspace), [sampling metrics](../results/workspace/metrics.json) |
| Trajectories and pick/place | [Walkthrough: useful motion](engineering_walkthrough.md#3-give-the-tool-a-useful-job) | [Planner](../src/robotarm/planning/trajectories.py), [task code](../src/robotarm/simulation/tasks.py), [motion results](../results/trajectories) |
| Loads, structure and drives | [Mechanical analysis](03_mechanical_analysis.md) | [Calculation source](../analysis), [mechanical results](../results/mechanical) |
| Gripper force and travel | [Gripper mechanism](03_mechanical_analysis.md#gripper-mechanism) | [Gripper source](../src/robotarm/gripper/model.py), [finger-length plot](../results/research/finger_length.png) |
| PID feedback | [Walkthrough: control](engineering_walkthrough.md#6-test-how-a-simplified-joint-follows-commands) | [PID source](../src/robotarm/control/pid.py), [response/error plots](../results/control), [gain study](../results/research/pid_tuning.png) |
| Electronics and PCB | [Electronics chapter](05_electronics.md), [component/BOM guide](electronics_components.md) | [Schematic PDF](../electronics/exports/joint_interface.pdf), [PCB layers PDF](../electronics/exports/pcb_layers.pdf), [native project](../electronics) |
| Numerical research | [Research discussion](engineering_report.md#16-results-and-research-questions) | [Five parameter sweeps and plots](../results/research), [experiment source](../analysis/research_experiments.py) |
| Verification and reproducibility | [Validation matrix](validation_matrix.md), [project setup](../README.md#run) | [Tests](../tests), [executed checks](../results/validation), [isolated package evidence](../results/validation/packaging_validation.json) |

## Browse the evidence visually

| Geometry and motion | Mechanics and control |
|---|---|
| [Coordinate frames](../results/workspace/coordinate_frames.png) · [Workspace](../results/workspace/workspace_projections.png) | [Joint torque envelope](../results/mechanical/joint_torque.png) · [Payload sensitivity](../results/research/payload.png) |
| [Pick/place animation](../results/trajectories/pick_place_fk.gif) · [TCP path](../results/trajectories/pick_place_tcp.png) | [PID step response](../results/control/pid_step_response.png) · [PID tracking](../results/control/pid_tracking.png) |
| [Joint motion and derivatives](../results/trajectories/pick_place_joints.png) · [Gripper render](../cad/renders/gripper.png) | [Motion-duration study](../results/research/duration.png) · [Finger stiffness](../results/research/finger_length.png) |

[Open the interactive robot online](https://aster-six-engineering-showcase.warmkiwi64.chatgpt.site/#robot) for browser inspection, joint controls and playback without downloading files. The [project download and launch instructions](../../README.md) describe optional offline viewing and native CAD/KiCad editing. GitHub also previews images, Markdown and PDFs; its repository HTML links show source rather than executing the viewer.

## Read the claims with their evidence class

| Label | Meaning here |
|---|---|
| **TARGET** | Desired performance, including payload and repeatability; no physical measurement. |
| **ASSUMED** | Chosen model input, such as material properties, lumped masses, friction or controller inertia. |
| **CALCULATED** | An equation evaluated with stated inputs and simplifications. |
| **SIMULATED** | Output of a numerical model, such as task motion or PID tracking. |
| **VERIFIED DIGITALLY** | An executed test or native application check within its recorded rules and scope. |

The [KPI table](kpis.md) supplies values and their evidence classes. The [scope audit](digital_scope_audit.md) explains why analytical beams, simplified PID plants, representative collision screening and conceptual electronics satisfy this digital brief, while physical performance remains unverified.

## Review the engineering process

[Design decisions](design_decisions.md) record choices and tradeoffs. The [project journal](project_journal.md) records actual iterations and corrections. The [final review](final_review.md), [completion checklist](completion_checklist.md) and [release notes](release_notes.md) describe the resulting project. The [environment report](00_environment.md) records the toolchain used during development.
