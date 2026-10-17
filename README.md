# ASTER-6 · Six-axis robot arm and parallel gripper

**Version 1.2.0 · DIGITAL SCOPE COMPLETE · Digital engineering design**

An educational mechatronics project connecting original parametric CAD, robot kinematics, motion planning, PID control, analytical mechanics and a routed KiCad joint/sensor interface. The models, results and engineering decisions are reproducible from versioned source.

![Actual ASTER-6 CAD assembly](01_CAD_Models/Preview_Images/hero.png)

## Start here

[The project purpose and original goals](06_Complete_Project_Source/docs/project_alignment.md) explain how the mechanics, mathematics, motion, control and electronics connect into one digital engineering project.

[Download the complete v1.2.0 release](https://github.com/pratham-cloud-ctrl/industrial-robot-arm-digital-twin/releases/tag/v1.2.0) or clone this repository. Double-click **OPEN_PROJECT_HOME.cmd** for the project guide or **OPEN_3D_VIEWER.cmd** to view and move the robot. The viewer can isolate any of the 54 components and automatically fit it on screen. Use **OPEN_FREECAD_MODEL.cmd** for CAD editing and **OPEN_PCB_LAYOUT.cmd** for the KiCad board. These Windows launchers locate installed Chrome/Edge, FreeCAD and KiCad; they avoid incorrect file associations. On other systems, open [START_HERE.html](START_HERE.html) or [the interactive viewer](02_Simulation_and_Animation/Interactive_3D_Viewer.html) in a browser.

GitHub displays HTML source. Download the project to run its offline viewer.

## Review the project in five minutes

| Inspect | Start with | Continue with |
|---|---|---|
| Mechanical design | [Dimensioned drawings](01_CAD_Models/Drawings/engineering_interfaces.pdf) and [six poses](01_CAD_Models/Preview_Images/poses.png) | [54-part component catalog](06_Complete_Project_Source/docs/component_catalog.md) and [CAD methodology](06_Complete_Project_Source/docs/04_cad.md) |
| Robot theory | [Theory guide](06_Complete_Project_Source/docs/theory_guide.md) | [Kinematics](06_Complete_Project_Source/docs/02_kinematics.md), [mechanics](06_Complete_Project_Source/docs/03_mechanical_analysis.md) and [engineering report](06_Complete_Project_Source/docs/engineering_report.md) |
| Motion and control | [Workspace](02_Simulation_and_Animation/Workspace/workspace_3d.png), animation below and [PID tracking](02_Simulation_and_Animation/Control/pid_tracking.png) | [Recorded trajectories](02_Simulation_and_Animation/Trajectories) and [numerical software](06_Complete_Project_Source/src/robotarm) |
| Electronics | [Schematic PDF](04_Electronics/exports/joint_interface.pdf), [board layers](04_Electronics/exports/pcb_layers.pdf) and [component guide](06_Complete_Project_Source/docs/electronics_components.md) | [Electronics design](06_Complete_Project_Source/docs/05_electronics.md), [BOM](04_Electronics/bom.csv) and [fabrication files](04_Electronics/fabrication) |
| Verification | [Executed validation](06_Complete_Project_Source/results/validation/validation_report.md) and [requirements matrix](06_Complete_Project_Source/docs/validation_matrix.md) | [Independent review evidence](03_Reports_and_Results/Validation) and [software checks on GitHub](https://github.com/pratham-cloud-ctrl/industrial-robot-arm-digital-twin/actions/workflows/validation.yml) |

Native STEP/STL/FCStd and KiCad files are editable engineering data. Use the supplied app launchers or open them inside the appropriate application; PDF/PNG previews provide immediate viewing.

![Forward-kinematics line-model pick-and-place animation](02_Simulation_and_Animation/Trajectories/pick_place_fk.gif)

## Organized project folders

| Folder | Contents |
|---|---|
| [01_CAD_Models](01_CAD_Models) | FreeCAD and Blender models, STEP/STL assemblies and individual parts, drawings and renders |
| [02_Simulation_and_Animation](02_Simulation_and_Animation) | Offline interactive 3D viewer, pick/place data, workspace and PID results |
| [03_Reports_and_Results](03_Reports_and_Results) | Browser-readable engineering reports, mechanical/research data and validation evidence |
| [04_Electronics](04_Electronics) | Native KiCad schematic/PCB, BOM, board views, Gerbers/drill and verification reports |
| [05_Reference_and_Project_Notes](05_Reference_and_Project_Notes) | Index to original source documents and browser-readable reports |
| [06_Complete_Project_Source](06_Complete_Project_Source) | Reproducible CAD, analysis, software, tests, electronics generators and authoritative configuration |
| [07_Releases](07_Releases) | Versioned complete download and Python wheel information |

Presentation folders contain verified copies. The complete source folder is authoritative; regenerate outputs there and run `python scripts/sync_presentation.py` to refresh the organized copies. The copy hashes are in [ORGANIZATION_MANIFEST.json](ORGANIZATION_MANIFEST.json).

## Engineering and verification

Read the [engineering report](06_Complete_Project_Source/docs/engineering_report.md), [scope audit](06_Complete_Project_Source/docs/digital_scope_audit.md), [requirements matrix](06_Complete_Project_Source/docs/validation_matrix.md), [executed validation](06_Complete_Project_Source/results/validation/validation_report.md) and [detailed source README](06_Complete_Project_Source/README.md).

The robot has six revolute joints, 790 mm nominal shoulder-centred reach and a 90 mm parallel-jaw opening. Payload 4 kg and repeatability ±0.1 mm are design targets. No physical robot or electronics were built. Analytical stiffness, independent-axis PID, sampled clearance and conceptual PCB checks establish their stated digital scope; they do not establish certified hardware performance, EMC, production suitability or functional safety.

![Native KiCad view of the joint and sensor PCB](04_Electronics/exports/pcb_3d.png)

## Engineering process

Start from [requirements](06_Complete_Project_Source/docs/01_requirements.md), follow [architecture](06_Complete_Project_Source/docs/architecture.md) and [design decisions](06_Complete_Project_Source/docs/design_decisions.md), then compare calculations with the generated evidence. The [project journal](06_Complete_Project_Source/docs/project_journal.md) records actual faults, corrections and tool checks. CAD clearance is checked at named poses and sampled task configurations; the scope and limitations are recorded alongside the results.

The GitHub workflow checks numerical software, analytical regressions, lint, documentation, copied artifacts and saved electronics connectivity. Native KiCad ERC/DRC and full CAD checks are executed locally with the required engineering applications. [Reproduce the full validation](06_Complete_Project_Source/README.md#run) for those checks.

## Reproduce

From the cloned repository:

```bash
cd 06_Complete_Project_Source
python -m venv .venv
```

Activate the environment, then:

```bash
python -m pip install -e ".[cad,dev]"
python -m robotarm.demo --all
python scripts/run_validation.py --full
python scripts/sync_presentation.py
```

KiCad 10 is required for native electronics checks. Build123d and the numerical libraries are installed by the CAD/development extras. FreeCAD and Blender support independent CAD inspection and rendering. Detailed tool commands and engineering assumptions are in the source documentation.

MIT-licensed original source. Third-party software and libraries retain their licenses.
